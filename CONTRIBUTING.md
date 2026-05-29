# 贡献指南

感谢你对 AI Chief of Staff 的兴趣！这个项目欢迎任何形式的贡献。

## 🎯 你可以做什么

### 报告Bug
1. 先在 [Issues](../../issues) 中搜索是否已有相同问题
2. 如果没有，[创建新Issue](../../issues/new)，包括：
   - 你做了什么
   - 期望的结果
   - 实际的结果
   - 复现步骤
   - 系统/Docker/Python版本

### 提出功能建议
在 [Discussions](../../discussions) 或 [Issues](../../issues) 中描述：
- 你的使用场景
- 期望的功能
- 为什么现有功能不能满足

### 提交代码

1. **Fork本仓库**
2. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **本地开发**
   ```bash
   docker compose up -d --build
   docker compose exec fastapi alembic upgrade head
   ```
4. **测试改动**
5. **提交Pull Request**
   - 标题清晰描述改动
   - 关联相关Issue（如果有）
   - 在描述中说明改了什么、为什么改

## 🛠️ 开发环境

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/ai-chief-of-staff.git
cd ai-chief-of-staff

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 SILICONFLOW_API_KEY

# 启动服务
docker compose up -d --build
docker compose exec fastapi alembic upgrade head

# 查看日志
docker compose logs -f
```

## 📝 代码风格

- Python: 遵循 PEP 8
- 函数和类要有 docstring
- 中文注释优先（项目是面向中文用户）
- 提交消息格式：`类型: 简短描述`
  - `feat: 添加员工排行榜API`
  - `fix: 修复飞书token过期处理`
  - `docs: 更新部署文档`
  - `refactor: 重构task_graph状态管理`

## 🔍 测试

提交PR前请确保：

- [ ] `docker compose up -d --build` 成功启动
- [ ] `curl http://localhost:8000/health` 返回 `{"db":"ok","redis":"ok"}`
- [ ] Streamlit管理后台 http://localhost:8501 正常加载
- [ ] 你修改的功能在UI上能跑通

## 🌟 优先需要的贡献

- **多租户改造** — 让一套系统服务多个公司
- **测试用例** — 提高代码可靠性
- **文档完善** — 翻译、示例、最佳实践
- **企业微信/钉钉适配** — 不依赖飞书的客户也能用
- **Web前端** — 替换Streamlit，做更专业的UI

## 💬 沟通

- 简单问题：在Issue中评论
- 设计讨论：在Discussions中开新主题
- 紧急问题：邮件联系（在README中）

## 📜 开源协议

提交即表示同意将你的贡献按 [Apache 2.0](LICENSE) 协议发布。

---

再次感谢你的贡献！🎉
