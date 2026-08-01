# 4399AccountRegister

4399 全自动账号注册机

## 文件结构

```
src/main/
├── register.py          # 4399 协议注册主程序
├── vm_scheduler.py      # VM 调度器
├── main.go              # Go 版本
├── ZHUCEJI/
│   ├── github_register.py  # GitHub 注册模块
│   ├── identities/         # 身份文件目录
│   │   ├── kazeiro-nova-7349.json
│   │   ├── kazeiro-nova-1.json
│   │   └── ...
│   └── config.json
└── 4399ocr/             # OCR 模型
```

## 使用方法

1. 安装依赖: `pip install -r requirements.txt`
2. 配置身份文件（填入你的 GitHub Token）
3. 运行: `python register.py`

## 配置身份文件

编辑 `ZHUCEJI/identities/` 下的 JSON 文件，填入你的 GitHub Token：

```json
{
  "username": "your-username",
  "token": "ghp_xxxxxxxxxxxx",
  "owner": "your-username",
  "repo": "4399AccountRegister",
  "workflow_id": "register.yml",
  "enabled": true
}
```
