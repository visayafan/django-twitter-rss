
本项目可以生成 Twitter RSS 订阅源。

## 依赖

Python版本为3.6，Django版本为2.1。

依赖模块可以用命令 `pip install -r requirements.txt` 来安装。

## 运行

运行命令为 `python manage.py runserver`， 运行成功后访问 `http://127.0.0.1:8000`可打开首页，首页提供了通过 Twitter 链接得到 Twitter 订阅源的方法。


## 说明

- 所有繁体转为简体。
- 对于原样显示的链接进行隐藏，显示为`网页链接`。
- 递归显示转发的推特。

## 截图

![](static/images/图片显示.png)
