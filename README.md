# getfreenodes

本项目实现了自动化注册、登录、节点信息采集与协议组合，并自动同步到 GitHub。

## 功能简介
- 自动读取 `auto_register/getnodelist.txt` 中的节点获取网址
- 检测节点接口返回值，自动注册账号（优先 Gmail，遇到邮箱/滑动/Cloudflare 验证自动跳过）
- 登录并获取节点数据，自动组合成 SS/VMess 等协议链接
- 节点信息输出到 `nodes/nodes.txt`
- 所有代码和节点信息自动同步到本仓库
- 支持 GitHub Actions 定时自动运行与推送

## 目录结构
```
auto_register/
  get_all_nodes.py         # 主脚本，自动注册/登录/采集/组合节点
  getnodelist.txt          # 节点获取接口列表（每行一个）
  requirements.txt         # 依赖
.github/
  workflows/
    update_nodes.yml       # GitHub Actions 自动化配置
nodes/
  nodes.txt                # 自动生成的节点信息
README.md                  # 项目说明
```

## 使用方法
1. 在 `auto_register/getnodelist.txt` 填写节点获取接口，每行一个
2. 运行 `python auto_register/get_all_nodes.py` 自动采集节点
3. 节点信息会输出到 `nodes/nodes.txt`
4. 通过 `git add . && git commit -m "xxx" && git push` 可同步所有更改到 GitHub
5. GitHub Actions 会定时自动运行并推送最新节点

## 自动化说明
- Actions 每 6 小时自动运行一次，采集并推送节点信息
- 注册时遇到邮箱验证码/滑动/Cloudflare 验证会自动跳过该站点
- 支持多站点批量采集

## 免责声明
本项目仅供学习与交流，严禁用于任何非法用途！ 
