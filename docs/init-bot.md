23-01-12更新：目前采用 `start.py` 来同时启动Api和Bot。若想单独启动Api或Bot，需取消 `api.py/main.py` 的底部注释

# 如何开始？

保证你的Windows/Linux中`Python`版本高于`3.8`，执行下面的安装库命令

更新Python的方法可以参考本wiki的 [01-How_to_update_Python](https://github.com/Aewait/Valorant-Kook-Bot/wiki/01-How_to_update_Python)

~~~
pip3 install -r requirements.txt
~~~

> Q：为何`khl.py`只需要3.6.8以上版本，而本仓库需要3.8+？
>
> A：因为valorant的第三方`Python Api`需要3.8+版本

建议根据[khl.py](https://github.com/TWT233/khl.py)的`example`教程，学习KOOK机器人的基本搭建（很简单的，相信我）

如果你已经学习完了所有example，那么本仓库的内容对于你来说就是不难的！

我会添加一些只有本仓库中包含的内容的代码解释，方便你来搭建你自己的kook机器人！

### 1.克隆本仓库

准备好Linux下的git，克隆本仓库

~~~
git clone https://github.com/Aewait/Valorant-kaiheila-bot.git
~~~

如果想使用最新的commit和新功能，请切换到develop分支

### 2.配置config文件

在`code`路径下创建`config`文件夹，并在其中创建`config.json`，将你的`token`写入其中

~~~json
{
  "token": "bot websocket token",
  "img_upload_token": "用来上传图片进行测试的bot websocket token，建议新开一个不用的bot",
  "api_bot_token":"用来上传图片进行测试的bot websocket token，建议新开一个不用的bot",
  "caiyun":"彩云小译的token",
  "master_id":"bot作者的user_id，用于控制只有bot作者才能用的命令",
  "debug_ch":"用于发送debug消息的文字频道id"
  "img_upload_channel":"用于发送商店自定义背景图测试消息的文字频道id"
}
~~~

总结一下，本仓库需要手动配置的文件有下面两个，其中`color_emoji.json`在仓库中有示例文件

| 文件路径                    | 功能                                                         |
| --------------------------- | ------------------------------------------------------------ |
| code/config/config.json     | 存放本机器人的基本配置：[KOOK开发者页面](https://developer.kaiheila.cn/doc/intro) |
| ~code/config/valorant.json~ | ~存放拳头开发者api-key：[Roit Develop](https://developer.riotgames.com/)~ 目前需要使用该api的代码都已被删除 |
| ~code/config/caiyun.json~     | ~存放彩云小译的api-key：[彩云](https://docs.caiyunapp.com/blog/2018/09/03/lingocloud-api/#python-%E8%B0%83%E7%94%A8)~ 已使用`config.json`代替 |
| [code/config/color_emoji.json](https://github.com/Aewait/Kook-Valorant-Bot/blob/develop/code/config/color_emoji.json) | 存放`code/main.py`中自动给用户上角色功能相关的emoji以及`msg_id/guild_id`       |

这些文件已经被我写入了`.gitignore`，所以在本仓库中你是看不到该文件夹的。这也保证当我们把代码托管到`gitee/github/gitlab`等平台上时，自己的`token`不会泄漏

### 3.让机器人跑起来！


* 直接运行机器人

当你完成上面两步后，即可`cd`进入`code`目录，执行运行命令

~~~
python3 main.py
~~~

但是这样，你会发现程序在shell中挂起，且关闭终端后机器人会停止运行

* 让机器人后台运行(Linux)

下面这个代码的功能是让机器人在Linux后台运行，并将输出内容写入`code/log`路径下的`bot.log`文件。为了不让机器人的log也被他人看到，我也将log类型文件写入了`.gitignore`
```
nohup python3 -u main.py >> ./log/bot.log 2>&1&
```
执行后，Linux会给你返回一个进程编号（建议先用`python3 main.py`直接运行，确认无bug后再执行上面的命令）

* 找到后台运行的机器人并让其下岗(Linux)

我们可以通过`ps -e`查看当前正在运行的进程，但这样的缺点是，当你关闭shell后，下一次再打开，就会发现之前的进程貌似不见了。

这时候就可以用下面这个语句来**具体定位**之前已经在运行的后台程序

~~~
ps -aux|grep main.py|grep -v grep 
~~~

当你想让机器人下岗的时候，可以使用下面这个指令

```
kill -9 进程号
```

注意：如果你需要修改代码并测试新功能，请一定要先**终止先前在后台运行的程序**。否则你修改后的代码，即使用 `python3 main.py` 运行，其新功能也是无法生效的！

----

# 起飞！

好了！配置完本页面的内容，想必你的bot已经可以**正常起步**了！

在频道里面输入 `/Ahri`，让我们来看看本仓库里面一些函数的对应功能吧！