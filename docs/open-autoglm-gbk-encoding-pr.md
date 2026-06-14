# Open-AutoGLM 编码缺陷分析与 PR 准备

> 目的：记录我们在用 Open-AutoGLM 开发 SmartCart 时踩到的编码问题的**完整全程**，
> 作为后续 fork 仓库、修改、提 PR 的依据。所有结论均已在本机实测验证。

- 上游仓库：`https://github.com/zai-org/Open-AutoGLM`
- 本机环境：Windows 11（中文版），`locale.getpreferredencoding(False)` = **cp936（GBK）**
- 我们的 Python：3.13.1

---

## 一、背景：我们是怎么踩到的

SmartCart 的后端把 Open-AutoGLM 当**子进程**调用（`subprocess.run([sys.executable, "main.py", ...])`），
让它控制真机在淘宝/京东搜索，搜完后端再截屏交给 GLM-4V 提取商品。

在中文 Windows 上，第一次跑真实搜索时出现：

- 现象：AutoGLM 子进程像是卡住，最终**必然 300 秒超时**（我们设的 timeout），任务失败。
- 但手机上 AutoGLM 其实**已经完成**了淘宝搜索——卡住的是父进程这边的读取。

### 根因（我们这端）

`subprocess.run(..., text=True)` 在中文 Windows 上默认用 **GBK** 解码子进程 stdout。
而 Open-AutoGLM 运行时会向 stdout 打印 **emoji（🔍✅ 等）和中文**。emoji 是
GBK 无法解码的多字节序列，导致 Python 的**后台读取线程抛异常崩溃** → 管道缓冲区写满 →
子进程阻塞在写 stdout → 双方僵死 → 触发超时。

### 我们这端的修复（commit `e1cb8ac`，只是"消费端"的一半）

```python
# backend/skills/taobao_search.py
env['PYTHONIOENCODING'] = 'utf-8'          # 让子进程稳定按 UTF-8 输出
result = subprocess.run(
    [...],
    capture_output=True, text=True,
    encoding='utf-8', errors='replace',     # 父进程也按 UTF-8 解码
    timeout=300,
)
```

这解决了**我们调用它**时的问题。但根因——**Open-AutoGLM 自身代码依赖平台默认编码**——
还在上游。任何中文 Windows 用户**直接运行**它，照样会崩。这正是值得提 PR 的地方。

---

## 二、根因：依赖"平台默认编码"

Python 在 Windows 上：
- `print()` 走 `sys.stdout`，其编码取决于控制台代码页（中文 Windows 默认 **GBK/cp936**）。
- `open(path)`（文本模式不带 `encoding=`）默认用 `locale.getpreferredencoding()`（中文 Windows = **cp936**）。

只要内容里有 GBK 装不下的字符（emoji）或文件本身是 UTF-8，就会抛 `UnicodeEncodeError` /
`UnicodeDecodeError`。上游有**两类**这样的写法。

---

## 三、上游代码的具体问题

### 缺陷 A：emoji `print` 到 GBK 控制台 → `UnicodeEncodeError`

`main.py`（用户跑的主入口，启动自检阶段）：

| 行 | 代码 |
|----|------|
| `main.py:56` | `print("🔍 Checking system requirements...")` |
| `main.py:105` | `print(f"✅ OK ({version_line ...})")` |
| `main.py:207/232/240/265` | `print("✅ ...")` |
| `main.py:288` | `print("🔍 Checking model API...")` |
| `main.py:310` | `print("✅ OK")` |

`check_env.py`（README 引导用户第一步运行的环境自检脚本）通篇 emoji：
`print("🔍 ...")`、`print("✓ ...")`、`print("📝 ...")`、`print("⚠ ...")`、`print("✅ ...")`
（行 24/28/46/81/90 等）。

**触发条件**：控制台编码为 GBK（中文 Windows 默认的 cmd.exe / 旧 PowerShell 即是）。
用户运行的第一条命令 `python check_env.py` 或 `python main.py` 立刻崩在第一个 emoji。

### 缺陷 B：`open()` 不带 `encoding=` → 读 UTF-8 文件 `UnicodeDecodeError`

| 行 | 代码 | 读的内容 |
|----|------|----------|
| `check_env.py:12` | `with open(env_path) as f:` | `.env` |
| `test_api.py:13` | `with open(env_path) as f:` | `.env` |
| `test_phone.py:16` | `with open(env_path) as f:` | `.env` |
| `scripts/check_deployment_cn.py:66` | `with open(args.messages_file) as f:` 然后 `json.load(f)` | 含中文的消息 JSON |

中文 Windows 上 `open()` 默认 cp936；文件若是 UTF-8（含中文/emoji），轻则乱码重则
`UnicodeDecodeError`。`check_deployment_cn.py` 读的就是中文消息文件，命中概率极高。

### 铁证：项目自己其它地方写对了

`setup.py:6`：
```python
with open("README.md", "r", encoding="utf-8") as f:
```
说明团队**知道**正确写法，上面那些是**疏漏**，不是设计选择——这让 PR 非常站得住脚。

---

## 四、可复现的最小证据（本机实测）

```python
import locale
locale.getpreferredencoding(False)      # -> 'cp936'   （open() 的默认编码）

# 缺陷 A：emoji 无法被 GBK 编码（与平台无关，GBK 码表里就没有 emoji）
'🔍'.encode('gbk')   # UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f50d'
'✅'.encode('gbk')   # UnicodeEncodeError: ... '✅'
'⚠'.encode('gbk')    # UnicodeEncodeError: ... '⚠'
'📝'.encode('gbk')   # UnicodeEncodeError: ... '\U0001f4dd'
'蓝牙耳机'.encode('gbk')   # 正常 —— 证明崩的是 emoji，不是中文

# 缺陷 B：open() 默认 cp936 读 UTF-8 文件
open('t.txt','w',encoding='utf-8').write('# 配置\nKEY=蓝牙🔍\n')
open('t.txt').read()    # 在 cp936 默认下读含 emoji 的 UTF-8 → 解码异常/乱码
```

---

## 五、影响面

- **命中项目主力人群**：中文 Windows 用户（仓库 README、check_env、部署脚本全中文，受众明确）。
- **命中最早一步**：环境自检 / 主入口启动自检，用户还没用上核心功能就崩，劝退率高。
- **症状有迷惑性**：作为子进程被调用时表现为"卡死/超时"，不易定位到编码。

---

## 六、修复方案（PR 内容）

### 1. `open()` 统一加 `encoding="utf-8"`（缺陷 B，4 处）

```python
# check_env.py:12 / test_api.py:13 / test_phone.py:16
with open(env_path, encoding="utf-8") as f:

# scripts/check_deployment_cn.py:66
with open(args.messages_file, encoding="utf-8") as f:
```

### 2. 终端输出不依赖控制台编码（缺陷 A）

最小侵入、跨平台、对齐现代 Python 实践——在 CLI 入口（`main.py`、`check_env.py` 顶部）
把标准流重配为 UTF-8：

```python
import sys
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")   # Python 3.7+
    except Exception:
        pass
```

> 备选：把 emoji 换成 ASCII 标记（`[OK]`/`[!]`）。但 reconfigure 改动更小、保留观感、
> 且与缺陷 B 的修复理念一致（显式 UTF-8，不赌平台默认）。两案可在 PR 里讨论。

### 3. 回归保障

新增/补一个最小测试：在 cp936 语境下，自检脚本能跑完不抛 `UnicodeEncodeError`；
`open()` 能正确读 UTF-8 的 `.env` / 消息文件。

---

## 七、PR 执行计划

1. `fork` `zai-org/Open-AutoGLM` 到自己账号。
2. 新分支，例如 `fix/windows-utf8-encoding`。
3. 改动范围**克制**：仅上述 open() 4 处 + 两个 CLI 入口的 stdout reconfigure（不动业务逻辑）。
4. 自测：在中文 Windows（GBK 控制台）跑 `python check_env.py`、`python main.py` 验证不再崩。
5. PR 描述要点：
   - 标题：`fix: ensure UTF-8 for console output and file reads on Windows (GBK locale)`
   - 正文：现象（中文 Windows 直接崩在自检）+ 根因（依赖平台默认编码）+ 复现（上面的最小片段）+
     佐证（`setup.py` 已用 `encoding="utf-8"`，本 PR 只是补齐一致性）+ 改动清单。
   - 附上我们作为下游消费者踩坑的真实场景（subprocess 读 stdout 超时），增强说服力。

---

## 八、备注（诚实边界）

- 我们**已确认**缺陷 A、B 的存在与可复现性，但**尚未**在干净的中文 cmd.exe（强制 chcp 936）里
  跑完整 `main.py` 全流程截图留证——提 PR 前应补这一步真机/真控制台证据，做到每个断言都有据。
- 本机当前 `sys.stdout.encoding` 恰为 utf-8（被某些设置改过），但 `open()` 默认仍是 cp936；
  PR 复现说明里应明确"默认中文 Windows 控制台为 GBK"这一前提，避免审阅者环境不一致产生误解。
