# 岗位能力图谱系统

> 多源异构数据驱动岗位和能力图谱构建与动态演化分析系统（竞赛方案端到端 MVP）

本系统以**招聘 JD、简历、技术社区、课程认证、行业报告**等多源异构数据为输入，构建**版本化时序岗位—能力知识图谱**，实现从「数据采集 → 可信治理 → 新岗位发现 → 既有岗位更新 → 时序演化分析 → 简历解析 → 人岗匹配 → 学习路径推荐」的**全流程闭环**。

核心创新点：**可信度评分**（源权威 + 时效 + 跨源一致 + 抽取质量 − 重复风险 − 幻觉风险）、**抄袭/噪声/通胀/时滞四类数据治理**、**LLM 幻觉防控**（证据 span 强制落地）、**时序动态图谱**、**新岗位发现**、**细粒度人岗匹配**、**人在回路的审核机制**。

---

## 一、快速开始

### 环境要求

- Python 3.10+
- 可选 Docker（容器化部署）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 一键运行（推荐）

```bash
# 生成模拟数据 -> 运行评测 -> 启动 Web 服务
python run.py
```

启动后访问：

- 前端 Web 界面：<http://localhost:8000/>
- API 文档（Swagger）：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>

### 分步运行

```bash
# 1. 生成模拟数据（110 条 JD、20 份简历、金标准标注）
python scripts/generate_data.py

# 2. 一键评测（输出六大指标 + 生成 evaluation_report.json）
python scripts/evaluate.py

# 3. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 一键评测 + 测试覆盖率

```bash
bash scripts/run_eval.sh
# 等价于：生成数据 -> 评测 -> pytest --cov
```

---

## 二、项目结构

```
.
├── app/                     # 核心引擎（纯 Python，可独立测试）
│   ├── config.py            # 配置加载（支持 JSON 深合并 + 环境变量覆盖）
│   ├── models.py            # 领域模型（Job/Skill/Resume/Claim/RoleDefinition/MatchResult...）
│   ├── trust.py             # 可信度评分（六维加权）
│   ├── dedup.py             # 近重复检测（SimHash + MinHash）
│   ├── skills.py            # 技能本体（别名归一化 + 词典抽取）
│   ├── llm.py               # 可插拔 LLM 抽象（MockExtractor / SparkExtractor）
│   ├── ingest.py            # 数据接入与治理管线（质量标签）
│   ├── graph.py             # 版本化时序知识图谱（NetworkX + JSON 持久化）
│   ├── roles.py             # 新岗位发现 + 既有岗位动态更新
│   ├── resume_match.py      # 简历解析 + 人岗匹配 + 学习路径（技能先修 DAG）
│   ├── evaluation.py        # 评测指标计算
│   ├── pipeline.py          # 端到端编排管线（复用引擎）
│   └── main.py              # FastAPI 应用（API 契约）
├── config/default.json      # 默认配置（权重/阈值/源权威表）
├── scripts/
│   ├── generate_data.py     # 模拟数据生成（含抄袭/时滞/通胀注入）
│   ├── evaluate.py          # 一键评测
│   └── run_eval.sh          # 数据 + 评测 + 测试覆盖率
├── tests/                   # 42 个测试（35 单元 + 7 API）
├── web/
│   ├── index.html           # 前端单文件应用（Vue 3.5 + Element Plus 2.14 + ECharts 5.5.1）
│   └── webfonts/            # FontAwesome 图标字体
├── run.py                   # 一键启动
├── Dockerfile / docker-compose.yml
├── requirements.txt
└── .env.example             # 环境变量模板
```

---

## 三、功能模块与对应需求（FR 映射）

| 模块 | 需求 | 说明 |
|------|------|------|
| 数据接入与治理 | FR-01 / FR-02 | 多源接入、近重复检测、质量标签、可信度评分 |
| 结构化抽取 | FR-03 | LLM 抽象层，Mock 规则抽取 + 讯飞星火骨架，携带证据 span |
| 新岗位发现 | FR-04 | 标题簇聚类 + 跨源一致性 + 萌芽度打分 |
| 既有岗位更新 | FR-05 | 时间窗对比，输出新增/删除/修改能力 |
| 时序动态图谱 | FR-06 | NetworkX 版本化图谱，支持时间切片与回滚 |
| 简历解析 | FR-07 | 技能/年限/学历/项目/证书提取 |
| 人岗匹配 | FR-08 | 硬门槛 + 五维评分 + 差距分析 + 可解释 |
| 学习路径 | FR-09 | 技能先修 DAG 拓扑排序 |
| 人在回路审核 | FR-10 | Claim 审核状态流转 |
| 评测体系 | FR-11 | 六大指标自动对照金标准 |

---

## 四、可信度评分模型

```
Trust(e) = w_s·SourceAuthority + w_t·Freshness + w_c·CrossSourceAgreement
         + w_q·ExtractionQuality − w_d·DuplicationRisk − w_h·HallucinationRisk
```

- **源权威**：企业官网 0.95 > 行业报告 0.85 > 课程认证 0.80 > 招聘平台 0.70 > 技术社区 0.60 > 简历 0.45
- **判决阈值**：`trust_score ≥ 0.75` 发布，`0.45 ~ 0.75` 进入人工复核，`< 0.45` 拒绝
- **幻觉防控**：每条 Claim 强制携带 `evidence_span`，无证据支撑却发布的结论计入幻觉率

---

## 五、数据治理（四大风险）

1. **抄袭检测**：SimHash（64 位，海明距离 ≤3 分桶）+ MinHash（128 排列，Jaccard ≥0.82），字符级 3-gram shingle 捕捉逐字复制
2. **噪声治理**：空字段 / 乱码 / 无技能 / 描述过短质量标签
3. **技能通胀**：区分「必备」与「加分」段抽取，稀有技能占比识别堆砌
4. **时滞治理**：`valid_from / valid_to` 时间有效性，新鲜度半衰期 365 天

---

## 六、评测指标（已达标）

| 指标 | 目标 | 实测 |
|------|------|------|
| JD 解析 F1 | ≥ 0.90 | **0.989** |
| 简历技能提取 F1 | ≥ 0.90 | **0.976** |
| 人岗匹配准确率 | ≥ 0.90 | **0.950** |
| 重复识别 F1 | — | **1.000** |
| 证据覆盖率 | — | **1.000** |
| 幻觉率 | — | **0.000** |
| 单元测试覆盖率 | ≥ 60% | **76%**（42 个测试全通过） |

测试规模：110 条 JD、20 份简历、280 条匹配样本。运行 `bash scripts/run_eval.sh` 可复现。

---

## 七、前端界面

前端为**单 HTML 文件应用**（`web/index.html`，~2700 行），基于 Vue 3.5 + Element Plus 2.14 + ECharts 5.5.1，无需构建工具，由 FastAPI 直接托管静态文件。

### 主题系统

支持**暗色 / 亮色双主题**实时切换。通过 `[data-theme="light"]` CSS 选择器覆盖全部语义色 Token（`--color-bg-*`、`--color-text-*`、`--color-border-*`、`--color-primary-*` 等），Element Plus 组件同步适配。所有 ECharts 图表（力导向图、饼图、柱状图、雷达图）的 tooltip、标签、连线颜色均跟随主题动态切换。

### 全景图谱（增强版）

采用**双栏布局**：左侧力导向图 + 右侧信息面板，提供丰富的交互能力：

- **搜索高亮**：实时搜索框，匹配节点放大高亮，未匹配节点淡化至 opacity 0.15
- **筛选控制**：行业、级别下拉筛选，联动图谱重新渲染
- **缩放与重置**：放大 / 缩小 / 重置视图 / 刷新布局四个快捷按钮
- **节点点击详情**：点击任意节点，右侧面板展示类型、行业、级别、趋势、可信度、关联数、关联技能（可点击跳转高亮）、关联岗位
- **行业分布饼图**：ECharts 环形图，按岗位数量统计行业分布
- **热门增长技能**：水平条形图，按技能类别统计增长 / 萌芽技能占比
- **高级图例**：节点类型（岗位 / 技能 / 增长技能）+ 关系类型（必备 / 加分）+ 交互提示（点击 / 拖拽）
- **节点视觉增强**：角色节点按可信度缩放尺寸，增长技能带橙色发光边框，tooltip 毛玻璃效果

### 其他页面

- **新岗位发现**：候选岗位卡片，展示萌芽度、核心职责、必备 / 加分技能、典型场景
- **岗位演化**：时间窗对比，展示能力新增 / 删除 / 修改
- **人岗匹配**：简历上传 / 粘贴 → 雷达图 + 五维条形图 + 技能匹配 / 缺失 + 诊断解释 + 学习路径
- **数据治理**：可信度评分模型、来源权威性、时效性饼图、数据质量柱状图、幻觉率监控
- **评测指标**：六大指标达成情况柱状图 + 测试方案概览

### 设计与工程

- **Design Tokens**：4px 基线网格、7 级字号、6 级圆角、5 级阴影、4 条动效曲线
- **无障碍（A11y）**：`:focus-visible` 焦点环、`aria-label` / `role`、`.sr-only` 类、触控目标 ≥ 40px、打印媒体查询
- **性能优化**：`contain: layout style` 限制重绘、`will-change` 合成层提示、`font-variant-numeric: tabular-nums` 防数字跳动
- **响应式**：≤ 1200px 平板横屏适配、≤ 768px 移动端适配（隐藏侧栏、单栏布局）

---

## 八、API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/ingestion/jobs` | 数据接入 + 治理 |
| POST | `/api/v1/roles/discover` | 新岗位发现 |
| GET | `/api/v1/roles` | 已标准化岗位列表 |
| GET | `/api/v1/roles/{name}/timeline` | 岗位能力演化对比 |
| GET | `/api/v1/graph/panorama` | 全景图谱（行业/级别过滤） |
| GET | `/api/v1/graph/versions` | 图谱版本列表 |
| POST | `/api/v1/resumes/parse` | 简历文本解析 |
| POST | `/api/v1/resumes/upload` | 简历文件上传（PDF/Word） |
| POST | `/api/v1/matching/diagnose` | 人岗匹配诊断 |
| POST | `/api/v1/learning-paths` | 学习路径推荐 |
| POST | `/api/v1/reviews/{id}/approve` | 人在回路审核 |
| GET | `/api/v1/metrics/evaluation` | 评测报告 |

---

## 九、可插拔 LLM 抽取

系统默认使用 `MockExtractor`（规则 + 技能词典，无需 API 即可跑通全流程）。切换真实大模型（讯飞星火）：

```bash
export SPARK_API_KEY=your_key
export JOB_GRAPH_LLM_PROVIDER=spark
```

或在 `config/default.json` 将 `llm.provider` 改为 `spark`。抽取结果统一符合 `app/llm.py` 中的 JSON Schema，携带证据 span。自定义其他 LLM 只需实现 `LLMExtractor` 协议（`extract_job` / `extract_resume`）。

---

## 十、Docker 部署

```bash
# 构建并启动（首次启动自动生成数据 + 评测）
docker compose up --build

# 或单容器
docker build -t job-ability-graph .
docker run -p 8000:8000 -v $(pwd)/data:/app/data job-ability-graph
```

容器内置健康检查（`/health`），数据卷挂载 `data/` 持久化图谱。

---

## 十一、配置说明

默认配置 `config/default.json`，可用环境变量 `JOB_GRAPH_CONFIG` 指向自定义 JSON 做深合并覆盖。主要配置项：

- `trust.weights`：可信度六维权重
- `trust.thresholds`：发布/复核/拒绝阈值
- `sources.authority`：各数据源权威分
- `dedup.*`：SimHash/MinHash 阈值
- `matching.weights`：匹配五维权重
- `trend.*`：趋势分析时间窗与增长率阈值

---

## 十二、测试

```bash
python -m pytest tests/ -q                # 42 个测试
python -m pytest tests/ --cov=app         # 含覆盖率报告（76%）
```

---

## 十三、设计说明与已知限制

- **Mock 抽取**为规则化近似，用于端到端验证；接真实 LLM 后抽取质量依赖提示词与 schema 约束。
- **图谱存储**为轻量嵌入式（NetworkX + JSON），适合竞赛演示；生产可平滑替换为 Neo4j。
- **新岗位发现**采用标题精确聚类策略，适合「已出现但未标准化」的岗位；更复杂的语义聚类可在 `roles.py` 扩展。
- 评审阈值、匹配权重均可通过 `config/default.json` 调整，无需改代码。

详细技术路线见仓库内两份方案文档（`XH-202621_技术路线与需求文档.md` 与比赛方案 md）。
