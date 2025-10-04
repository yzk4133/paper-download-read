# arXiv 文献解析与知识汇总平台

一个前后端分离的科研效率工具，支持从 arXiv 自动检索并下载 PDF、解析结构化摘要信息，并导出 Excel 汇总报告。项目采用 **React + Ant Design** 构建现代化前端界面，**Flask + Flask-RESTX** 提供后端 API 服务，并为后续接入通义千问等大模型解析预留扩展点。

## ✨ 核心能力

- **论文检索与下载**：基于 arXiv API，支持关键词、年份范围与最大下载数量限制，自动命名并存储 PDF。
- **解析任务编排**：预留 PDF 文本抽取、LLM 调用、Excel 导出等服务模块，可按需完善业务逻辑。
- **实时交互界面**：React 前端提供爬取配置、解析控制、结果预览与导出等模块，体验清晰直观。
- **工程化架构**：后端采用模块化服务层 + RESTful API，前端拆分为组件/路由/服务目录，方便长期维护与协作。

## 🧱 技术栈

| 领域 | 技术 | 用途 |
| --- | --- | --- |
| **前端** | React 18, Vite, Ant Design 5, axios, react-router-dom, dayjs, lodash | 组件化 UI、路由导航、HTTP 请求、数据处理 |
| **后端** | Flask, Flask-RESTX, Flask-CORS, requests, PyPDF2, pandas, openpyxl, langchain-openai, python-dotenv | API 服务、跨域支持、PDF 下载、数据处理、Excel 导出、LLM 关键词与摘要 |
| **大模型** | 通义千问 SDK（待接入） | 解析论文文本，提取创新点/实验方法/结论 |
| **基础设施** | logging, pathlib | 统一日志、文件路径管理 |

## 📁 目录结构

```
arXiv_Download_Site/
├─ backend/
│  ├─ app/
│  │  ├─ __init__.py           # Flask 应用工厂，注册配置、日志、蓝图
│  │  ├─ api/                  # RESTX 命名空间（crawl/parse/excel）
│  │  ├─ services/             # 业务服务层（爬取、解析、Excel 导出等）
│  │  ├─ utils/                # 工具函数（校验、日志、目录管理）
│  │  └─ config/               # 多环境配置（开发 / 生产）
│  ├─ pdf_files/               # 下载的论文 PDF
│  ├─ excel_output/            # 导出的 Excel 报表
│  ├─ logs/                    # 运行日志
│  ├─ requirements.txt         # 后端依赖
│  └─ run.py                   # 后端入口（python backend/run.py）
│
├─ frontend/
│  ├─ public/                  # 静态资源（Vite 模板）
│  ├─ src/
│  │  ├─ assets/               # 前端静态资源
│  │  ├─ components/           # UI 组件（Common/CrawlConfig/ParseControl/ResultPreview）
│  │  ├─ context/              # React Context，全局状态
│  │  ├─ hooks/                # 自定义 Hooks（解析进度、Excel 状态轮询）
│  │  ├─ pages/                # 页面（Home + Result）
│  │  ├─ routes/               # 路由配置
│  │  ├─ services/             # axios API 封装
│  │  ├─ utils/                # 工具函数（校验、格式化）
│  │  ├─ App.jsx / main.jsx    # 入口组件
│  ├─ package.json             # 前端依赖与脚本
│  ├─ vite.config.js           # Vite 配置（端口 + 代理）
│  ├─ .env.development         # 本地 API 地址
│  └─ .env.production          # 生产环境 API 地址占位
│
├─ README.md                   # 项目文档（当前文件）
└─ pdf_files/ (legacy)         # 旧版 Flask 模式遗留，可按需清理
```

> 🔧 `services/pdf_service.py`、`services/llm_service.py`、`services/excel_service.py` 目前为占位文件，可在接入对应功能时补充实现。

## 🚀 快速上手

### 1. 克隆并安装依赖

```bash
# 后端依赖
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

> 如果使用 PowerShell，激活虚拟环境命令为 `.venv\Scripts\Activate.ps1`。

### 2. 启动后端（Flask）

```bash
# 在项目根目录执行（确保已激活虚拟环境）
python run.py
```

默认在 `http://127.0.0.1:5000` 提供 API 接口，并在 `/api/docs` 暴露 Swagger 文档。

> 如需启用不同环境配置，可设置 `ARXIV_APP_CONFIG` 环境变量为 `development` 或 `production`，并在 `backend/app/config` 目录中完善对应配置类。

### 通义千问配置（可选）

若希望启用大模型自动生成关键词与解析摘要，可在仓库根目录或 `backend/` 目录新增 `.env` 文件（与 `run.py` 同级），填入以下变量：

```
TONGYI_API_KEY=你的通义千问API密钥
TONGYI_LLM_MODEL=qwen-turbo          # 可按需替换为其它兼容模型
TONGYI_LLM_TEMPERATURE=0             # 可选，控制输出发散度
TONGYI_LLM_MAX_TOKENS=1024           # 可选，控制最大生成长度
```

未配置密钥时，系统会退回本地启发式规则，仍可运行但不具备 LLM 智能摘要能力。

### 3. 启动前端（React）

```bash
cd frontend
npm run dev
```

本地开发默认运行在 `http://127.0.0.1:3000`，通过 Vite 代理访问后端 `/api`。

若需要自定义后端地址，可在 `frontend/.env.development` 与 `frontend/.env.production` 中调整 `VITE_API_BASE_URL`，修改后需重新启动前端服务。

### 4. 构建与预览前端

```bash
cd frontend
npm run build
npm run preview
```

第一条命令会在 `frontend/dist` 生成生产构建，第二条命令则本地预览打包结果。

### 5. 体验流程

1. 在首页输入**研究需求描述**，系统会调用大模型生成检索关键词；也可补充「附加关键词」、调整生成数量，并自定义 PDF/Excel 保存目录。
2. 提交后可在关键词列表中查看实际使用的检索词，必要时点击「查看结果」跳转到结果页；若暂未解析，可继续在首页启动解析。
3. 在「解析控制」中启动解析任务，前端会实时轮询 `/parse/progress` 展示完成度，并在进度面板中展示当前解析目录。
4. 结果页支持一键返回首页重新检索；「导出工具」可生成 Excel，并展示最新文件名与输出目录。

## ⚙️ 配置与拓展

- **日志与产物目录**：默认位于 `backend/logs`、`backend/pdf_files`、`backend/excel_output`。如需自定义，可在配置类中修改 `BASE_DIR` 与相关路径常量。
- **Excel/解析服务**：`backend/app/services` 中的 `pdf_service.py`、`llm_service.py`、`parse_service.py`、`excel_service.py` 已提供基于 PyPDF2 + 启发式摘要的 baseline，可在此基础上接入真实 LLM、改造异步流程或自定义 Excel 模板。
- **自定义主题**：前端样式集中在 `frontend/src/styles.css` 与各组件样式属性，可结合 Ant Design 自定义主题或设计系统。
- **代码质量**：前端提供 `npm run lint` 执行 ESLint；后端可结合 `flake8`、`black` 等工具（未默认集成，可按需补充）。

## ❓ 常见问题

| 场景 | 解决方案 |
| --- | --- |
| PowerShell 激活虚拟环境提示权限不足 | 以管理员身份运行 PowerShell 或执行 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 后重试 |
| 前端运行时报找不到 API | 确认后端已启动，或在 `.env` 中改为 `http://127.0.0.1:5000/api` |
| 生产打包后静态资源 404 | 确认部署时将 `frontend/dist` 整体作为静态根目录，同时确保后端代理 `/api` 路由保持可用 |
| 需要 HTTPS 访问 | 在 Vite 配置中启用 `server.https` 或使用 Nginx/反向代理终止 TLS |

## 🧩 后续扩展建议

- 将 `services/llm_service.py` 中的启发式解析替换为真实的大模型调用（通义千问/Qwen、GPT 等），补充 API 密钥管理与重试策略。
- 引入后台任务队列（如 Celery + Redis）或异步 worker，将 PDF 解析与 Excel 导出改为异步执行并推送实时进度。
- 优化 Excel 报告版式：支持多 sheet、图表和高亮格式，同时允许导出 CSV/JSON 等多种格式。
- 在前端增加解析结果的筛选/排序与关键字搜索，提供「重新解析」或「导出单条」等操作入口。
- 添加用户认证与操作审计，为多人协同或云端部署打基础。

## 📝 许可证

本项目仍遵循 MIT License，允许自由使用、修改和分发。