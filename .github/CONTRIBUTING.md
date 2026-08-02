# 贡献指南

感谢你考虑为 BiliSum Research 做出贡献！本文档将指导你如何参与项目开发。

> 本 fork 的强制交付规则以
> [`docs/development/delivery-workflow.md`](../docs/development/delivery-workflow.md) 为准：
> 所有变更必须经过 **Issue → topic branch → PR → required checks/review → merge**，
> 禁止直接 push、force-push 或绕过保护修改 `master`；Release 只能基于合入后的主干发布。

---

## 📋 贡献流程

### 1. 报告 Bug → 创建 Issue

如果你发现了 bug，请先检查是否已有相关 Issue，然后使用 **Bug 报告模板**创建新 Issue：

1. 访问 [Issues 页面](https://github.com/aaronfang/BiliSum-Research/issues/new/choose)
2. 选择 "🐛 Bug 报告" 模板
3. 填写完整信息（复现步骤、环境、日志等）
4. 等待维护者确认

### 2. 提出新功能 → 创建 Feature Request

在开始开发新功能前，请先创建 **Feature Request**：

1. 使用 "✨ 功能请求" 模板创建 Issue
2. 详细描述使用场景和预期效果
3. 等待讨论和确认可行性
4. **获得维护者批准后再开始开发**

### 3. 提交代码 → Pull Request

#### 必须遵守的规则

⚠️ **PR 前必须先创建 Issue**

所有 PR 必须关联并关闭一个已存在的 Issue，文档修正和维护变更也不例外。如果没有相关
Issue，请先创建。

#### 开发步骤

1. **Fork 项目**并 clone 到本地

```bash
git clone https://github.com/your-username/BiliSum.git
cd BiliSum
```

2. **创建分支**（从 `master` 分支创建）

```bash
git checkout -b fix/issue-123-subtitle-error
# 或
git checkout -b feat/issue-456-local-llm
```

**分支命名规范**：
- `fix/issue-{number}-{description}` - Bug 修复
- `feat/issue-{number}-{description}` - 新功能
- `docs/issue-{number}-{description}` - 文档更新
- `refactor/issue-{number}-{description}` - 代码重构

3. **安装依赖**

```bash
# Python 依赖
pip install -e ".[dev]"

# 桌面应用依赖
cd apps/desktop
npm install
```

4. **开发并测试**

```bash
# 运行单元测试
pytest tests/unit/ -v

# 运行桌面应用开发模式
npm run dev

# 构建验证
npm run build
```

5. **提交变更**（遵循 Conventional Commits）

```bash
git add .
git commit -m "fix(subtitle): 修复 B站字幕解析空指针异常

- 添加 subtitle_url 存在性检查
- 处理字幕列表为空的情况
- 新增单元测试覆盖边界场景

Closes #123"
```

6. **Push topic branch（禁止 push `master`）**

```bash
git push origin fix/issue-123-subtitle-error
```

7. **创建 Pull Request**

- 访问 GitHub 页面，点击 "Compare & pull request"
- 填写 PR 模板（关联 Issue、描述变更、测试步骤）
- 等待 CI 检查通过
- 等待代码审查

---

## 📝 Commit 规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(knowledge): 支持本地 LLM` |
| `fix` | Bug 修复 | `fix(subtitle): 修复字幕时间戳解析错误` |
| `docs` | 文档更新 | `docs(readme): 更新安装步骤` |
| `style` | 代码格式 | `style(lint): 修复 ESLint 警告` |
| `refactor` | 代码重构 | `refactor(api): 提取重复的错误处理逻辑` |
| `perf` | 性能优化 | `perf(transcribe): 优化 FunASR 批处理` |
| `test` | 测试相关 | `test(subtitle): 新增字幕选择优先级测试` |
| `build` | 构建相关 | `build(deps): 升级 pydantic 到 v2` |
| `chore` | 构建/配置 | `chore(ci): 添加 Python 3.12 支持` |
| `security` | 安全修复 | `security(api): 修复 SSRF 漏洞` |

### Scope 范围（可选）

常用范围：
- `subtitle` - 字幕相关
- `transcribe` - 转写相关
- `summary` - 摘要生成
- `knowledge` - 知识库
- `desktop` - 桌面应用
- `web` - Web 界面
- `api` - API 接口
- `runtime` - 运行时环境
- `ci` - CI/CD

### Subject 主题

- 使用中文或英文，简洁描述变更
- 不超过 72 字符
- 使用祈使句（"修复"而非"修复了"）

### Body 正文（可选）

- 详细说明变更内容和原因
- 每行不超过 100 字符
- 可以包含多个段落

### Footer 页脚

- **关联 Issue**: `Closes #123` 或 `Fixes #456`
- **Breaking Changes**: `BREAKING CHANGE: API 参数结构变更`

### ✅ 良好示例

```
feat(knowledge): 支持自定义 Embedding 模型

- 新增 HuggingFace 镜像配置
- 支持自定义模型 ID
- 添加模型下载和验证功能

Closes #123
```

```
fix(security): 修复 B站字幕 URL SSRF 漏洞

添加域名白名单验证，防止攻击者通过伪造字幕 URL 探测内网服务。

- 限制字幕 URL 只能来自 bilibili.com, hdslb.com
- 强制使用 HTTPS 协议
- 新增 URL 验证单元测试

Fixes #456
```

### ❌ 不良示例

```
修复了一个 bug  # 没有 type 和 scope，描述不清晰
```

```
feat: add feature  # 描述过于简单
```

---

## 🧪 测试要求

### 必须遵守

- ✅ **所有测试必须通过**：`pytest tests/unit/ -v`
- ✅ **新功能必须有测试**：覆盖核心逻辑和边界情况
- ✅ **Bug 修复必须有回归测试**：防止问题再次出现

### 运行测试

```bash
# 运行所有单元测试
pytest tests/unit/ -v

# 运行特定测试文件
pytest tests/unit/test_bilibili_subtitle.py -v

# 查看测试覆盖率
pytest --cov=video_sum_service --cov-report=html
```

### 编写测试

测试文件位于 `tests/unit/`，使用 pytest 框架：

```python
def test_fetch_subtitle_with_valid_url():
    """测试有效 URL 的字幕获取"""
    result = fetch_bilibili_subtitle(aid=12345, cid=67890)
    assert result is not None
    assert "transcript" in result
```

---

## 📐 代码规范

### Python

- 使用 **Type Hints**（类型注解）
- 遵循 **PEP 8** 编码规范
- 函数和类使用 **docstring**
- 复杂逻辑添加注释

```python
def fetch_bilibili_subtitle(
    aid: int,
    cid: int,
    cookie: str | None = None,
    bvid: str | None = None,
) -> dict[str, object] | None:
    """从 B站获取视频字幕

    优先级：UP主上传 > AI中文 > 其他中文 > 首个可用

    Args:
        aid: 视频 AV 号
        cid: 分 P 的 CID
        cookie: B站 Cookie（可选）
        bvid: 视频 BV 号（可选）

    Returns:
        包含 transcript 和 segments 的字典，失败返回 None
    """
    # 实现...
```

### TypeScript/React

- 使用 **TypeScript**，避免 `any`
- React 组件使用 **函数组件 + Hooks**
- 使用 **ESLint** 检查代码

```typescript
interface SubtitleData {
  transcript: string;
  segments: Array<{
    start: number;
    end: number;
    text: string;
  }>;
}

function useSubtitle(videoId: string): SubtitleData | null {
  // 实现...
}
```

---

## 🎨 项目结构

```
BiliSum/
├── apps/
│   ├── desktop/          # Electron 桌面应用
│   │   ├── electron/     # Electron 主进程
│   │   └── src/          # React 前端
│   ├── service/          # FastAPI 后端服务
│   └── web/              # Web 静态资源
├── packages/
│   ├── core/             # 核心业务逻辑
│   ├── infra/            # 基础设施层
│   └── npx/              # CLI 工具（已废弃）
├── tests/
│   └── unit/             # 单元测试
├── docs/                 # 文档
└── scripts/              # 工具脚本
```

---

## 🔍 代码审查

PR 提交后会进行代码审查：

### 审查标准

1. **功能正确性**：是否解决了 Issue 中的问题
2. **代码质量**：可读性、可维护性、复杂度
3. **测试覆盖**：是否有足够的测试
4. **安全性**：是否引入安全风险（SSRF、注入、路径遍历等）
5. **性能**：是否影响性能
6. **文档**：是否更新了相关文档

### 反馈处理

- 审查意见会以评论形式给出
- 请及时响应并修改代码
- 修改后 push 到同一分支，PR 会自动更新
- 所有讨论解决后，维护者会合并 PR

---

## ❓ 常见问题

### Q: 我可以直接提 PR 吗？

A: **不可以**。所有变更（包括文档修正）都必须先创建 Issue。

### Q: 我的 PR 多久会被审查？

A: 通常在 3-5 个工作日内。复杂的 PR 可能需要更长时间。

### Q: 我不熟悉 Python/TypeScript，可以贡献吗？

A: 可以！你可以：
- 报告 Bug
- 改进文档
- 翻译文档
- 设计 UI/UX
- 提供测试反馈

### Q: 我的 PR 被拒绝了怎么办？

A: 不要气馁！阅读拒绝原因，讨论改进方案，或尝试其他贡献方式。

---

## 📞 联系我们

- **GitHub Issues**: https://github.com/aaronfang/BiliSum-Research/issues
- **LinuxDO 社区**: https://linux.do/t/topic/2175871

---

感谢你的贡献！🎉
