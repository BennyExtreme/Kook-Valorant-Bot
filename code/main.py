# encoding: utf-8:
import os, io
import random
import time
import traceback
from datetime import datetime, timedelta
from typing import Union
import aiohttp
import copy
import zhconv
import asyncio
from khl import (Bot, Event, EventTypes, Message, PrivateMessage, requester, Channel)
from khl.card import Card, CardMessage, Element, Module, Types, Struct
from aiohttp import client_exceptions
from PIL import Image, UnidentifiedImageError  # 用于合成图片

from utils import ShopRate, ShopImg, Help, GrantRoles, Translate, BotVip, Other
from utils.log import BotLog
from utils.log.Logging import _log
from utils.valorant import ValFileUpd
from utils.KookApi import (icon_cm, status_active_game, status_active_music, status_delete, bot_offline, upd_card,
                           get_card)
from utils.valorant.Val import *
from utils.valorant.EzAuth import EzAuth, EzAuthExp
from utils.Gtime import GetTime, GetTimeStampOf8AM

# bot的token文件
from utils.FileManage import config, bot, ApiAuthLog, Save_All_File
# 只用来上传图片的bot
bot_upimg = Bot(token=config['token']['img_upload_token'])

# 设置全局变量：机器人开发者id/报错频道
master_id = config['master_id']

#在bot一开机的时候就获取log频道作为全局变量
debug_ch: Channel
cm_send_test: Channel
NOTIFY_NUM = 3  # 非vip用户皮肤提醒栏位
VIP_BG_SIZE = 4  # vip用户背景图片数量限制
RATE_LIMITED_TIME = 180  # 全局登录速率超速等待秒数
Login_Forbidden = False  # 403错误禁止所有用户登录
#记录开机时间
start_time = GetTime()


# 向botmarket通信
@bot.task.add_interval(minutes=30)
async def botmarket():
    api = "http://bot.gekj.net/api/v1/online.bot"
    headers = {'uuid': 'a87ebe9c-1319-4394-9704-0ad2c70e2567'}
    async with aiohttp.ClientSession() as session:
        await session.post(api, headers=headers)


# 每5分钟保存一次文件
@bot.task.add_interval(minutes=5)
async def Save_File_Task():
    try:
        await Save_All_File()
    except:
        err_cur = f"ERR! [{GetTime()}] [Save.File.Task]\n```\n{traceback.format_exc()}\n```"
        _log.error(err_cur)
        await bot.client.send(debug_ch, err_cur)


@bot.command(name='kill')
async def KillBot(msg: Message, num: str = '124124', *arg):
    BotLog.logMsg(msg)
    if msg.author_id == master_id and int(num) == config['no']:
        # 保存所有文件
        await Save_All_File(False)
        await msg.reply(f"[KILL] 保存全局变量成功，bot下线")
        res = await bot_offline()  # 调用接口下线bot
        _log.info(f"KILL | bot-off: {res}\n")
        os._exit(0)  # 退出程序
    else:
        await msg.reply(f"您没有权限或参数错误！\n本Bot编号为：{config['no']}")


##########################################################################################
########################################  help  ##########################################


# hello命令，一般用于测试阿狸在不在线
@bot.command(name='hello', aliases=['HELLO'])
async def world(msg: Message):
    BotLog.logMsg(msg)
    await msg.reply('你好呀~')


# help命令,触发指令为 `/Ahri`,因为help指令和其他机器人冲突
@bot.command(name='Ahri', aliases=['ahri', '阿狸'])
async def Ahri(msg: Message, *arg):
    BotLog.logMsg(msg)
    try:
        cm = Help.help_main(start_time)
        await msg.reply(cm)
    except Exception as result:
        await BotLog.BaseException_Handler("ahri", traceback.format_exc(), msg, debug_send=debug_ch)


# help命令(瓦洛兰特相关)
@bot.command(name='Vhelp', aliases=['vhelp'])
async def Vhelp(msg: Message, *arg):
    BotLog.logMsg(msg)
    try:
        cm = Help.help_val()
        await msg.reply(cm)
    except Exception as result:
        await BotLog.BaseException_Handler("vhelp", traceback.format_exc(), msg, debug_send=debug_ch)


# 当有人@机器人的时候进行回复，可识别出是否为机器人作者
@bot.on_message()
async def atAhri(msg: Message):
    try:
        me = await bot.client.fetch_me()
        if f"(met){me.id}(met)" in msg.content:
            BotLog.logMsg(msg)
            if msg.author_id == master_id:
                text = Help.help_develop()
                await msg.reply(text)
            else:
                await msg.reply(f"呀，听说有人想我了，是吗？\n输入`/ahri` 或 `/vhelp` 打开帮助面板，和阿狸一起玩吧！")
            _log.info(f"Au:{msg.author_id} | msg.reply success!")
    except:
        await BotLog.BaseException_Handler("at_help", traceback.format_exc(), msg)


#################################################################################################
########################################## others ###############################################


# 倒计时函数，单位为秒，默认60秒
@bot.command()
async def countdown(msg: Message, time: int = 60, *args):
    BotLog.logMsg(msg)
    if args != ():
        await msg.reply(f"参数错误，countdown命令只支持1个参数\n正确用法: `/countdown 120` 生成一个120s的倒计时")
        return
    elif time <= 0 or time >= 90000000:
        await msg.reply(f"倒计时时间超出范围！")
        return
    try:
        cm = CardMessage()
        c1 = Card(Module.Header('本狸帮你按下秒表喽~'), color=(198, 65, 55))  # color=(90,59,215) is another available form
        c1.append(Module.Divider())
        c1.append(Module.Countdown(datetime.now() + timedelta(seconds=time), mode=Types.CountdownMode.SECOND))
        cm.append(c1)
        await msg.reply(cm)
    except Exception as result:
        await BotLog.BaseException_Handler("countdown", traceback.format_exc(), msg, debug_send=debug_ch)


# 掷骰子 saying `!roll 1 100` in channel,or `/roll 1 100 5` to dice 5 times once
@bot.command()
async def roll(msg: Message, t_min: int = 1, t_max: int = 100, n: int = 1, *args):
    BotLog.logMsg(msg)
    if args != ():
        await msg.reply(
            f"参数错误，roll命令只支持3个参数\n正确用法:\n```\n/roll 1 100 生成一个1到100之间的随机数\n/roll 1 100 3 生成三个1到100之间的随机数\n```")
        return
    elif t_min >= t_max:  #范围小边界不能大于大边界
        await msg.reply(f'范围错误，必须提供两个参数，由小到大！\nmin:`{t_min}` max:`{t_max}`')
        return
    elif t_max >= 90000000:  #不允许用户使用太大的数字
        await msg.reply(f"掷骰子的数据超出范围！")
        return
    try:
        result = [random.randint(t_min, t_max) for i in range(n)]
        await msg.reply(f'掷出来啦: {result}')
    except Exception as result:
        await BotLog.BaseException_Handler("roll", traceback.format_exc(), msg, debug_send=debug_ch)


# 返回天气
@bot.command(name='we')
async def Weather(msg: Message, city: str = "err"):
    BotLog.logMsg(msg)
    if city == "err":
        await msg.reply(f"函数参数错误，城市: `{city}`\n")
        return

    try:
        await Other.weather(msg, city)
    except Exception as result:
        await BotLog.BaseException_Handler("Weather", traceback.format_exc(), msg, debug_send=debug_ch)


################################ grant roles for user ##########################################


# 在不修改代码的前提下设置上色功能的服务器和监听消息
@bot.command()
async def Color_Set_GM(msg: Message, Card_Msg_id: str):
    BotLog.logMsg(msg)
    if msg.author_id == master_id:
        await GrantRoles.Color_SetGm(msg, Card_Msg_id)


# 判断消息的emoji回应，并给予不同角色
@bot.on_event(EventTypes.ADDED_REACTION)
async def Grant_Roles(b: Bot, event: Event):
    await GrantRoles.Color_GrantRole(b, event)


# 给用户上色（在发出消息后，机器人自动添加回应）
@bot.command(name='Color_Set', aliases=['color_set'])
async def Color_Set(msg: Message):
    BotLog.logMsg(msg)
    if msg.author_id == master_id:
        await GrantRoles.Color_SetMsg(bot, msg)


# 感谢助力者（每天19点进行检查）
@bot.task.add_cron(hour=19, minute=0, timezone="Asia/Shanghai")
async def thanks_sponser():
    await GrantRoles.THX_Sponser(bot)


######################################## Translate ################################################


# 普通翻译指令
@bot.command(name='TL', aliases=['tl'])
async def translation(msg: Message, *arg):
    BotLog.logMsg(msg)
    await Translate.translate_main(msg, ' '.join(arg))


#查看当前占用的实时翻译栏位
@bot.command()
async def CheckTL(msg: Message):
    BotLog.logMsg(msg)
    await msg.reply(f"目前已使用栏位:{Translate.checkTL()}/{len(Translate.ListTL)}")


# 关闭所有栏位的实时翻译（避免有些人用完不关）
@bot.command(name='ShutdownTL', aliases=['SDTL'])
async def ShutdownTL(msg: Message):
    BotLog.logMsg(msg)
    if msg.author.id != master_id:
        return  #这条命令只有bot的作者可以调用
    await Translate.Shutdown_TL(bot, msg)


# 通过频道id判断是否实时翻译本频道内容
@bot.command(regex=r'(.+)')
async def TL_Realtime(msg: Message, *arg):
    if msg.ctx.channel.id in Translate.ListTL:  #判断频道是否已开启实时翻译
        word = " ".join(arg)
        # 不翻译关闭实时翻译的指令
        if word == "/TLOFF" or word == "/tloff" or word == '/tlon' or word == '/TLON':
            return
        # 翻译
        BotLog.logMsg(msg)
        await Translate.translate_main(msg, ' '.join(arg))


# 开启实时翻译功能
@bot.command(name='TLON', aliases=['tlon'])
async def TLON(msg: Message):
    BotLog.logMsg(msg)
    await Translate.Open_TL(msg)


# 关闭实时翻译功能
@bot.command(name='TLOFF', aliases=['tloff'])
async def TLOFF(msg: Message):
    BotLog.logMsg(msg)
    await Translate.Close_TL(msg)


###########################################################################################
####################################以下是游戏相关代码区#####################################
###########################################################################################


# 开始打游戏
@bot.command()
async def gaming(msg: Message, game: int = 1):
    BotLog.logMsg(msg)
    #await bot.client.update_playing_game(3,1)# 英雄联盟
    if game == 1:
        ret = await status_active_game(453027)  # 瓦洛兰特
        await msg.reply(f"{ret['message']}，阿狸上号valorant啦！")
    elif game == 2:
        ret = await status_active_game(3)  # 英雄联盟
        await msg.reply(f"{ret['message']}，阿狸上号LOL啦！")


# 开始听歌
@bot.command()
async def singing(msg: Message, music: str = "err", singer: str = "err"):
    BotLog.logMsg(msg)
    if music == "err" or singer == "err":
        await msg.reply(f"函数参数错误，music: `{music}` singer: `{singer}`")
        return

    ret = await status_active_music(music, singer)
    await msg.reply(f"{ret['message']}，阿狸开始听歌啦！")


# 停止打游戏1/听歌2
@bot.command(name='sleeping')
async def sleeping(msg: Message, d: int = 1):
    BotLog.logMsg(msg)
    ret = await status_delete(d)
    if d == 1:
        await msg.reply(f"{ret['message']}，阿狸下号休息啦!")
    elif d == 2:
        await msg.reply(f"{ret['message']}，阿狸摘下了耳机~")
    #await bot.client.stop_playing_game()


# 拳头api调用被禁止的时候用这个变量取消所有相关命令
async def Login_Forbidden_send(msg: Message):
    _log.info(f"Au:{msg.author_id} Command Failed")
    await msg.reply(
        f"拳头api登录接口出现了一些错误，开发者已禁止所有相关功能的使用\n[https://img.kookapp.cn/assets/2022-09/oj33pNtVpi1ee0eh.png](https://img.kookapp.cn/assets/2022-09/oj33pNtVpi1ee0eh.png)"
    )


# 手动设置禁止登录的全局变量状态
@bot.command(name='lf')
async def Login_Forbidden_Change(msg: Message):
    BotLog.logMsg(msg)
    if msg.author_id == master_id:
        global Login_Forbidden
        if Login_Forbidden:
            Login_Forbidden = False
        else:
            Login_Forbidden = True

        await msg.reply(f"Update Login_Forbidden status: {Login_Forbidden}")


# 存储用户游戏id
@bot.command(name="saveid", case_sensitive=False)
async def saveid(msg: Message, *args):
    BotLog.logMsg(msg)
    if args == ():
        await msg.reply(f"您没有提供您的游戏id：`{args}`")
        return
    try:
        game_id = " ".join(args)  #避免用户需要输入双引号
        await saveid_main(msg, game_id)
    except Exception as result:
        await BotLog.BaseException_Handler("saveid", traceback.format_exc(), msg)


# 已保存id总数
@bot.command(name='saveid-a')
async def saveid_all(msg: Message):
    BotLog.logMsg(msg)
    try:
        await saveid_count(msg)
    except Exception as result:
        await BotLog.BaseException_Handler("saveid-a", traceback.format_exc(), msg)


# 实现读取用户游戏ID并返回
@bot.command(name="myid", case_sensitive=False) 
async def myid(msg: Message, *args):
    BotLog.logMsg(msg)
    try:
        await myid_main(msg)
    except Exception as result:
        await BotLog.BaseException_Handler("myid", traceback.format_exc(), msg)


# 查询游戏错误码
@bot.command(name='val', aliases=['van', 'VAN', 'VAL'])
async def val_err(msg: Message, numS: str = "-1", *arg):
    BotLog.logMsg(msg)
    try:
        await val_errcode(msg, numS)
    except Exception as result:
        await BotLog.BaseException_Handler("val", traceback.format_exc(), msg,help=f"您输入的错误码格式不正确！\n请提供正确范围的`数字`,而非`{numS}`")


#关于dx报错的解决方法
@bot.command(name='DX', aliases=['dx'])  # 新增别名dx
async def dx(msg: Message):
    BotLog.logMsg(msg)
    await dx123(msg)


###########################################vip######################################################

#用来存放roll的频道/服务器/回应用户的dict
from utils.FileManage import VipShopBgDict, VipRollDcit, UserPwdReauth, VipUserDict


# 新建vip的uuid，第一个参数是天数，第二个参数是数量
@bot.command(name="vip-a")
async def get_vip_uuid(msg: Message, day: int = 30, num: int = 10):
    BotLog.logMsg(msg)
    try:
        if msg.author_id == master_id:
            text = await BotVip.create_vip_uuid(num, day)
            cm = CardMessage()
            c = Card(Module.Header(f"已生成新的uuid   数量:{num}  天数:{day}"),
                     Module.Divider(),
                     Module.Section(Element.Text(text, Types.Text.KMD)),
                     color='#e17f89')
            cm.append(c)
            await msg.reply(cm)
            _log.info("vip-a | create_vip_uuid reply successful!")
        else:
            await msg.reply("您没有权限操作此命令！")
    except Exception as result:
        await BotLog.BaseException_Handler("vip-a", traceback.format_exc(), msg)


# 兑换vip
@bot.command(name="vip-u", aliases=['兑换'])
async def buy_vip_uuid(msg: Message, uuid: str = 'err', *arg):
    BotLog.logMsg(msg)
    if uuid == 'err':
        await msg.reply(f"只有输入vip的兑换码才可以操作哦！uuid: `{uuid}`")
        return
    try:
        #把bot传过去是为了让阿狸在有人成兑换激活码之后发送消息到log频道
        ret = await BotVip.using_vip_uuid(msg, uuid, bot, debug_ch)
        global VipShopBgDict  #在用户兑换vip的时候就创建此键值
        VipShopBgDict['cache'][msg.author_id] = {'cache_time': 0, 'cache_img': None}
    except Exception as result:
        await BotLog.BaseException_Handler("vip-u", traceback.format_exc(), msg, debug_send=debug_ch)


# 看vip剩余时间
@bot.command(name="vip-c")
async def check_vip_timeremain(msg: Message, *arg):
    BotLog.logMsg(msg)
    try:
        if not await BotVip.vip_ck(msg):
            return
        # 获取时间
        ret_t = BotVip.vip_time_remain(msg.author_id)
        ret_cm = await BotVip.vip_time_remain_cm(ret_t)
        await msg.reply(ret_cm)
    except Exception as result:
        await BotLog.BaseException_Handler("vip-c", traceback.format_exc(), msg, debug_send=debug_ch)


# 看vip用户列表
@bot.command(name="vip-l")
async def list_vip_user(msg: Message, *arg):
    BotLog.logMsg(msg)
    try:
        if msg.author_id == master_id:
            text = await BotVip.fetch_vip_user()
            cm2 = CardMessage()
            c = Card(Module.Header(f"当前vip用户列表如下"), color='#e17f89')
            c.append(Module.Section(Element.Text(f"```\n{text}```", Types.Text.KMD)))
            cm2.append(c)
            await msg.reply(cm2)
        else:
            await msg.reply("您没有权限操作此命令！")
    except Exception as result:
        await BotLog.BaseException_Handler("vip-l", traceback.format_exc(), msg)


async def check_vip_img():
    _log.info("[BOT.TASK] check_vip_img start!")
    try:
        global VipShopBgDict
        cm0 = CardMessage()
        c = Card(color='#fb4b57')  #卡片侧边栏颜色
        text = f"您设置的vip背景图违规！请尽快替换"
        c.append(Module.Section(Element.Text(text, Types.Text.KMD), Element.Image(src=icon_cm.powder, size='sm')))
        c.append(Module.Context(Element.Text("多次发送违禁图片会导致阿狸被封，请您慎重选择图片！", Types.Text.KMD)))
        #遍历vip用户的图片
        log_str_user = "[BOT.TASK] check_vip_img Au:"
        for vip_user, vip_bg in VipShopBgDict['bg'].items():
            user = await bot.client.fetch_user(vip_user)
            sz = len(vip_bg["background"])
            i = 0
            while i < sz:
                try:
                    bg_test = Image.open(io.BytesIO(await ShopImg.img_requestor(vip_bg["background"][i])))
                    i += 1
                except UnidentifiedImageError as result:
                    err_str = f"ERR! [{GetTime()}] checking [{vip_user}] img\n```\n{result}\n"
                    #把被ban的图片替换成默认的图片，打印url便于日后排错
                    err_str += f"[UnidentifiedImageError] url={vip_bg['background'][i]}\n```"
                    c.append(Module.Section(Element.Text(err_str, Types.Text.KMD)))
                    cm0.append(c)
                    await user.send(cm0)  # 发送私聊消息给用户
                    await bot.client.send(debug_ch, err_str)  # 发送消息到debug频道
                    vip_bg["background"][i] = BotVip.illegal_img_169  #修改成16比9的图片
                    vip_bg["status"] = False  #需要重新加载图片
                    _log.error(err_str)
                except Exception as result:
                    err_str = f"ERR! [{GetTime()}] checking[{vip_user}]img\n```\n{traceback.format_exc()}\n```"
                    _log.error(err_str)
                    c.append(Module.Section(Element.Text(err_str, Types.Text.KMD)))
                    cm0.append(c)
                    await user.send(cm0)
                    await bot.client.send(debug_ch, err_str)

            # 遍历完一个用户后打印结果
            log_str_user += f"({vip_user})"

        #所有用户成功遍历后，写入文件
        _log.info(log_str_user)
        _log.info("[BOT.TASK] check_vip_img finished!")
    except Exception as result:
        err_str = f"ERR! [{GetTime()}] check_vip_img\n```\n{traceback.format_exc()}\n```"
        _log.exception("Exception occur")
        await bot.client.send(debug_ch, err_str)  # 发送消息到debug频道


#因为这个功能很重要，所以设置成可以用命令调用+定时任务
@bot.task.add_cron(hour=3, minute=0, timezone="Asia/Shanghai")
async def check_vip_img_task():
    await check_vip_img()


@bot.command(name="vip-img")
async def check_vip_img_task(msg: Message, *arg):
    BotLog.logMsg(msg)
    if msg.author_id == master_id:
        await check_vip_img()
        await msg.reply("背景图片diy检查完成！")
    else:
        await msg.reply("您没有权限执行此命令！")
        return


@bot.command(name="vip-shop")
async def vip_shop_bg_set(msg: Message, icon: str = "err", *arg):
    BotLog.logMsg(msg)
    if icon != 'err' and ('http' not in icon or '](' not in icon):
        await msg.reply(f"请提供正确的图片url！\n当前：`{icon}`")
        return

    try:
        if not await BotVip.vip_ck(msg):
            return

        x3 = "[None]"
        if icon != 'err':
            user_ind = (msg.author_id in VipShopBgDict['bg'])  #判断当前用户在不在dict中
            if user_ind and len(VipShopBgDict['bg'][msg.author_id]["background"]) >= VIP_BG_SIZE:
                cm = await get_card(f"当前仅支持保存{VIP_BG_SIZE}个自定义图片", "您可用「/vip-shop-d 图片编号」删除已有图片再添加", icon_cm.that_it)
                await msg.reply(cm)
                return

            #提取图片url
            x1 = icon.find('](')
            x2 = icon.find(')', x1 + 2)
            x3 = icon[x1 + 2:x2]
            _log.info(f"Au:{msg.author_id} get_url | {x3}")
            try:
                # 检查图片链接格式是否支持
                if ('png' not in x3) and ('jpg' not in x3) and ('jpeg' not in x3):
                    text = f"您当前上传的图片格式不支持！请上传png/jpg/jpeg格式的图片"
                    cm = await get_card(text, "请优先尝试png格式图片，其余格式兼容性有一定问题", icon_cm.ahri_dark)
                    await msg.reply(cm)
                    _log.info(f"Au:{msg.author_id} | img_type_not support")
                    return
                #打开图片(测试)
                bg_vip = Image.open(io.BytesIO(await ShopImg.img_requestor(x3)))
            except UnidentifiedImageError as result:
                err_str = f"ERR! [{GetTime()}] vip_shop_imgck\n```\n{result}\n```"
                _log.error(err_str)
                await msg.reply(f"图片违规！请重新上传\n{err_str}")
                return

            #到插入的时候再创建list，避免出现图片没有通过检查，但是list又被创建了的情况
            if not user_ind:
                VipShopBgDict['bg'][msg.author_id] = {}
                VipShopBgDict['bg'][msg.author_id]["background"] = list()
                #新建用户，但是有可能已经缓存了默认的背景图片，所以状态为false（重画）
                VipShopBgDict['bg'][msg.author_id]["status"] = False
            #插入图片
            VipShopBgDict['bg'][msg.author_id]["background"].append(x3)

        cm = await BotVip.get_vip_shop_bg_cm(msg)
        #先让测试bot把这个卡片发到频道，如果发出去了说明json没有问题
        await bot_upimg.client.send(cm_send_test, cm)
        _log.info(f"Au:{msg.author_id} | cm_send_test success")
        #然后阿狸在进行回应
        await msg.reply(cm)

        # 打印用户新增的图片日后用于排错
        _log.info(f"Au:{msg.author_id} img add | {x3}")

    except requester.HTTPRequester.APIRequestFailed as result:
        await BotLog.APIRequestFailed_Handler("vip_shop", traceback.format_exc(), msg, bot, cm)
        VipShopBgDict['bg'][msg.author_id]["background"].remove(x3)  #删掉里面的图片
        _log.error(f"Au:{msg.author_id} | remove({x3})")
    except Exception as result:
        await BotLog.BaseException_Handler("vip_shop", traceback.format_exc(), msg)


@bot.command(name="vip-shop-s")
async def vip_shop_bg_set_s(msg: Message, num: str = "err", *arg):
    BotLog.logMsg(msg)
    if num == 'err':
        await msg.reply(f"请提供正确的图片序号！\n当前：`{num}`")
        return
    try:
        global VipShopBgDict
        if not await BotVip.vip_ck(msg):
            return
        if msg.author_id not in VipShopBgDict['bg']:
            await msg.reply("您尚未自定义商店背景图！")
            return

        num = int(num)
        if num < len(VipShopBgDict['bg'][msg.author_id]["background"]):
            try:  #打开用户需要切换的图片
                bg_vip = Image.open(
                    io.BytesIO(await ShopImg.img_requestor(VipShopBgDict['bg'][msg.author_id]["background"][num])))
            except UnidentifiedImageError as result:
                err_str = f"ERR! [{GetTime()}] vip_shop_s_imgck\n```\n{result}\n```"
                await msg.reply(f"图片违规！请重新上传\n{err_str}")
                await BotVip.replace_illegal_img(msg.author_id, num)  #替换图片
                _log.exception("Exception occur")
                return
            # 图片检查通过，交换两个图片的位置
            icon_num = VipShopBgDict['bg'][msg.author_id]["background"][num]
            VipShopBgDict['bg'][msg.author_id]["background"][num] = VipShopBgDict['bg'][msg.author_id]["background"][0]
            VipShopBgDict['bg'][msg.author_id]["background"][0] = icon_num
            VipShopBgDict['bg'][msg.author_id]['status'] = False
            #修改图片之后，因为8点bot存储了商店图，所以需要重新获取 以新的背景图为背景 的商店图片
        else:
            await msg.reply("请提供正确返回的图片序号，可以用`/vip-shop`进行查看")
            return

        cm = await BotVip.get_vip_shop_bg_cm(msg)
        #先让测试bot把这个卡片发到频道，如果发出去了说明json没有问题
        await bot_upimg.client.send(cm_send_test, cm)
        _log.info(f"Au:{msg.author_id} | cm_send_test success")
        #然后阿狸在进行回应
        await msg.reply(cm)

        _log.info(f"Au:{msg.author_id} | switch to [{VipShopBgDict['bg'][msg.author_id]['background'][0]}]")
    except requester.HTTPRequester.APIRequestFailed as result:
        await BotLog.APIRequestFailed_Handler("vip_shop_s", traceback.format_exc(), msg, bot, cm)
    except Exception as result:
        await BotLog.BaseException_Handler("vip_shop_s", traceback.format_exc(), msg)


@bot.command(name="vip-shop-d")
async def vip_shop_bg_set_d(msg: Message, num: str = "err", *arg):
    BotLog.logMsg(msg)
    if num == 'err':
        await msg.reply(f"请提供正确的图片序号！\n当前：`{num}`")
        return
    try:
        if not await BotVip.vip_ck(msg):
            return
        if msg.author_id not in VipShopBgDict['bg']:
            await msg.reply("您尚未自定义商店背景图！")
            return

        num = int(num)
        if num < len(VipShopBgDict['bg'][msg.author_id]["background"]) and num > 0:
            # 删除图片
            del_img_url = VipShopBgDict['bg'][msg.author_id]["background"][num]
            del VipShopBgDict['bg'][msg.author_id]["background"][num]
        elif num == 0:
            await msg.reply("不支持删除当前正在使用的背景图！")
            return
        else:
            await msg.reply("请提供正确返回的图片序号，可以用`/vip-shop`进行查看")
            return

        cm = await BotVip.get_vip_shop_bg_cm(msg)
        #先让测试bot把这个卡片发到频道，如果发出去了说明json没有问题
        await bot_upimg.client.send(cm_send_test, cm)
        _log.info(f"Au:{msg.author_id} | cm_send_test success")
        #然后阿狸在进行回应
        await msg.reply(cm)

        _log.info(f"Au:{msg.author_id} | delete [{del_img_url}]")
    except requester.HTTPRequester.APIRequestFailed as result:
        await BotLog.APIRequestFailed_Handler("vip_shop_d", traceback.format_exc(), msg, bot, cm)
    except Exception as result:
        await BotLog.BaseException_Handler("vip_shop_d", traceback.format_exc(), msg)


# 判断消息的emoji回应，并记录id
@bot.on_event(EventTypes.ADDED_REACTION)
async def vip_roll_log(b: Bot, event: Event):
    global VipRollDcit
    if event.body['msg_id'] not in VipRollDcit:
        return
    else:
        user_id = event.body['user_id']
        # 把用户id添加到list中
        log_str = f"[vip-roll-log] Au:{user_id} roll_msg:{event.body['msg_id']}"
        if user_id not in VipRollDcit[event.body['msg_id']]['user']:
            VipRollDcit[event.body['msg_id']]['user'].append(user_id)
            channel = await bot.client.fetch_public_channel(event.body['channel_id'])
            await bot.client.send(channel, f"[添加回应]->抽奖参加成功！", temp_target_id=event.body['user_id'])
            log_str += " Join"  #有join的才是新用户

        _log.info(log_str)


# 开启一波抽奖
@bot.command(name='vip-r', aliases=['vip-roll'])
async def vip_roll(msg: Message, vday: int = 7, vnum: int = 5, rday: float = 1.0):
    BotLog.logMsg(msg)
    try:
        if msg.author_id != master_id:
            await msg.reply(f"您没有权限执行本命令")
            return
        # 设置开始抽奖
        global VipRollDcit
        cm = BotVip.roll_vip_start(vnum, vday, rday)
        roll_ch = await bot.client.fetch_public_channel(msg.ctx.channel.id)
        roll_send = await bot.client.send(roll_ch, cm)
        VipRollDcit[roll_send['msg_id']] = {  # type: ignore
            'time': time.time() + rday * 86400,
            'nums': vnum,
            'days': vday,
            'channel_id': msg.ctx.channel.id,
            'guild_id': msg.ctx.guild.id,
            'user': []
        }
        _log.info(f"card message send | C:{msg.ctx.channel.id}")
    except:
        await BotLog.BaseException_Handler("vip-r", traceback.format_exc(), msg)


@bot.task.add_interval(seconds=80)
async def vip_roll_task():
    global VipRollDcit, VipUserDict
    viprolldict_temp = copy.deepcopy(VipRollDcit)  #临时变量用于修改
    log_str = ''
    for msg_id, minfo in viprolldict_temp.items():
        if time.time() < minfo['time']:
            continue
        else:
            _log.info(f"[BOT.TASK] vip_roll_task msg:{msg_id}")
            vday = VipRollDcit[msg_id]['days']  # vip天数
            vnum = VipRollDcit[msg_id]['nums']  # 奖品数量
            # 结束抽奖
            log_str = f"```\n[MsgID] {msg_id}\n"
            send_str = "恭喜 "
            # 人数大于奖品数量
            if len(VipRollDcit[msg_id]['user']) > vnum:
                ran = random.sample(range(0, len(VipRollDcit[msg_id]['user'])), vnum)  # 生成n个随机数
            else:  # 生成一个从0到len-1的列表 如果只有一个用户，生成的是[0]
                ran = list(range(len(VipRollDcit[msg_id]['user'])))
            # 开始遍历
            for j in ran:
                user_id = VipRollDcit[msg_id]['user'][j]
                user = await bot.client.fetch_user(user_id)
                # 设置用户的时间和个人信息
                time_vip = BotVip.vip_time_stamp(user_id, vday)
                VipUserDict[user_id] = {'time': time_vip, 'name_tag': f"{user.username}#{user.identify_num}"}
                # 创建卡片消息
                cm = CardMessage()
                c = Card(
                    Module.Section(Element.Text("恭喜您中奖阿狸vip了！", Types.Text.KMD),
                                   Element.Image(src=icon_cm.ahri_kda2, size='sm')))
                c.append(Module.Context(Element.Text(f"您抽中了{vday}天vip，可用/vhelp查看vip权益", Types.Text.KMD)))
                c.append(
                    Module.Countdown(datetime.now() + timedelta(seconds=BotVip.vip_time_remain(user_id)),
                                     mode=Types.CountdownMode.DAY))
                c.append(Module.Divider())
                c.append(
                    Module.Section('加入官方服务器，即可获得「阿狸赞助者」身份组',
                                   Element.Button('来狸', 'https://kook.top/gpbTwZ', Types.Click.LINK)))
                cm.append(c)
                await user.send(cm)
                log_str += f"[vip-roll] Au:{user_id} get [{vday}]day-vip\n"
                send_str += f"(met){user_id}(met) "

            log_str += "```"
            send_str += "获得了本次奖品！"
            await bot.client.send(debug_ch, log_str)  #发送此条抽奖信息的结果到debug
            #发送结果到抽奖频道
            roll_ch = await bot.client.fetch_public_channel(VipRollDcit[msg_id]['channel_id'])
            cm1 = CardMessage()
            c = Card(Module.Header(f"🎊 阿狸vip {VipRollDcit[msg_id]['days']}天体验卡 🎊"),
                     Module.Section(Element.Text(send_str, Types.Text.KMD)),
                     Module.Context(Element.Text(f"本次抽奖结束，奖励已私信发送", Types.Text.KMD)))
            cm1.append(c)
            await bot.client.send(roll_ch, cm1)
            del VipRollDcit[msg_id]  #删除此条抽奖信息

    # 更新抽奖列表(如果有变化)
    if viprolldict_temp != VipRollDcit:
        _log.info(log_str)  # 打印中奖用户作为log


# 给所有vip用户添加时间，避免出现某些错误的时候浪费vip时间
@bot.command(name='vip-ta')
async def vip_time_add(msg: Message, vday: int = 1, *arg):
    BotLog.logMsg(msg)
    if msg.author_id != master_id:
        await msg.reply(f"您没有权限执行此命令！")
        return

    try:
        global VipUserDict
        # 给所有vip用户上天数
        for vip, vinfo in VipUserDict.items():
            time_vip = BotVip.vip_time_stamp(vip, vday)
            VipUserDict[vip]['time'] = time_vip

        await msg.reply(f"操作完成，已给所有vip用户增加 `{vday}` 天时长")
        _log.info(f"[vip_time_add] update VipUserDict")
    except:
        err_str = f"ERR! [{GetTime()}] vip_time_add\n```\n{traceback.format_exc()}\n```"
        await msg.reply(f"{err_str}")
        _log.exception("Exception occur")


#####################################################################################

# 预加载用户的riot游戏id和玩家uuid（登录后Api获取）
from utils.FileManage import UserRiotName, SkinNotifyDict, EmojiDict, SkinRateDict, ValBundleList

# 用来存放auth对象（无法直接保存到文件）
UserAuthDict = {'AP': {}}
# 判断夜市有没有开
NightMarketOff = False
# 全局的速率限制，如果触发了速率限制的err，则阻止所有用户login
login_rate_limit = {'limit': False, 'time': time.time()}
# 用来存放用户每天的商店（早八会清空）
UserShopCache = { 'clear_time':time.time(),'data':{}}
# 用户皮肤评分选择列表
UserRtsDict = {}
# 用户皮肤提醒选择列表
UserStsDict = {}
# valorant皮肤等级对应的kook自定义表情
ValItersEmoji = EmojiDict['val_iters_emoji']


def check_rate_err_user(kook_user_id: str)-> bool:
    """检查皮肤评分的错误用户（违规用户）

    Return:
    - kook_user_id in SkinRateDict['err_user']
    """
    return (kook_user_id in SkinRateDict['err_user'])


def isSame_Authuuid(kook_user_id:str) -> bool:
    """判断UserShopCache["data"]商店缓存中的riot用户uuid是否相等。如果不相等，需要获取新商店

    Return:
    - False: kook_user_id not in UserShopCache["data"]
    - UserShopCache["data"][kook_user_id]["auth_user_id"] == UserRiotName[kook_user_id]["auth_user_id"]
    """
    # 用户不在缓存中，也是错误的
    if kook_user_id not in UserShopCache["data"]:
        return False
    # 用户在，则判断uuid是否相等
    return UserShopCache["data"][kook_user_id]["auth_user_id"] == UserRiotName[kook_user_id]["auth_user_id"]

def isClear_UserShopCache() -> bool:
    """判断UserShopCache["data"]是否在当日早八被清空（避免定时任务没有正常执行）
    - True: 如果已经清空，则返回True且啥都不做
    - False: 如果没有清空，则清空并返回False（这一次请求需要调用api获取商店）
    """
    # 判断清空的时间戳是否大于当日早上8点时间戳
    global UserShopCache
    if UserShopCache["clear_time"] >= GetTimeStampOf8AM():
        return True
    else: # 如果不大于，则代表定时任务没有正常执行，清空dict并返回FALSE
        UserShopCache["data"] = {}
        return False


# 检查全局用户登录速率
async def check_GloginRate():
    global login_rate_limit
    if login_rate_limit['limit']:
        if (time.time() - login_rate_limit['time']) > RATE_LIMITED_TIME:
            login_rate_limit['limit'] = False  #超出180s解除
        else:  #未超出240s
            raise EzAuthExp.RatelimitError
    return True


#查询当前有多少用户登录了
@bot.command(name="ckau")
async def check_UserAuthDict_len(msg: Message):
    BotLog.logMsg(msg)
    sz = len(UserAuthDict)
    res = f"UserAuthDict_len: `{sz}`"
    _log.info(res)
    await msg.reply(res)


# 登录，保存用户的token
@bot.command(name='login')
async def login(msg: Message, user: str = 'err', passwd: str = 'err', apSave='', *arg):
    _log.info(f"Au:{msg.author_id} {msg.author.username}#{msg.author.identify_num} | /login {apSave}")
    BotLog.log_bot_user(msg.author_id)  #这个操作只是用来记录用户和cmd总数的
    global Login_Forbidden, login_rate_limit, UserRiotName, UserAuthDict
    if not isinstance(msg, PrivateMessage):  # 不是私聊的话，禁止调用本命令
        await msg.reply(f"为了避免您的账户信息泄漏，请「私聊」使用本命令！\n用法：`/login 账户 密码`")
        return
    elif passwd == 'err' or user == 'err':
        await msg.reply(f"参数不完整，请提供您的账户密码！\naccount: `{user}` passwd: `{passwd}`\n正确用法：`/login 账户 密码`")
        return
    elif Login_Forbidden:
        await Login_Forbidden_send(msg)
        return
    try:
        # 1.检查全局登录速率
        await check_GloginRate()  # 无须接收此函数返回值，直接raise
        # 2.发送开始登录的提示消息
        cm0 = await get_card("正在尝试获取您的riot账户token", "小憩一下，很快就好啦！", icon_cm.val_logo_gif)
        send_msg = await msg.reply(cm0)  #记录消息id用于后续更新

        # 3.登录，获取用户的token
        auth = EzAuth()
        resw = await auth.authorize(user, passwd)
        UserAuthDict[msg.author_id] = {"auth": auth, "2fa": auth.is2fa}  # 将对象插入
        # 3.1 没有成功，是2fa用户，需要执行/tfa命令
        if not resw['status']:
            cm1 = await get_card("登录中断，需要提供邮箱验证码", "请使用「/tfa 验证码」提供邮箱验证码", icon_cm.val_logo_gif)
            await upd_card(send_msg['msg_id'], cm1, channel_type=msg.channel_type)
            _log.info(f"login | 2fa user | Au:{msg.author_id}")  # 打印信息
            return

        # 4.如果没有抛出异常，那就是完成登录了，设置用户的玩家uuid+昵称
        UserRiotName[msg.author_id] = {'auth_user_id': auth.user_id, 'GameName': auth.Name, 'TagLine': auth.Tag}
        # 设置基础打印信息
        text = f"登陆成功！欢迎回来，{UserRiotName[msg.author_id]['GameName']}#{UserRiotName[msg.author_id]['TagLine']}"
        info_text = "当前cookie有效期为2~3天，有任何问题请[点我](https://kook.top/gpbTwZ)"

        # 5.如果是vip用户，则执行下面的代码
        if await BotVip.vip_ck(msg.author_id):
            global VipShopBgDict  #因为换了用户，所以需要修改状态码重新获取商店
            if msg.author_id in VipShopBgDict['bg']:
                VipShopBgDict['bg'][msg.author_id]['status'] = False
            # 用于保存cookie的路径,保存vip用户登录信息
            auth.save_cookies(f"./log/cookie/{msg.author_id}.cke")

        # 6.用户自己选择是否保存账户密码，默认是不保存的；2fa用户也不会保存
        if apSave == 'save' and (not auth.is2fa):
            # 不在这里再新建（用于保存阿狸使用账户密码重登的时间，告知用户）
            if msg.author_id not in UserPwdReauth:
                UserPwdReauth[msg.author_id] = {}
            UserAuthDict['AP'][msg.author_id] = {'a': user, 'p': passwd}
            info_text += "\n您选择了保存账户密码，cookie失效后将使用账户密码重登"

        # 7.发送登录成功的信息
        cm = await get_card(text, info_text, icon_cm.correct)
        await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)

        # 8.全部都搞定了，打印登录信息日志
        _log.info(
            f"[{GetTime()}] [Login] Au:{msg.author_id} - {UserRiotName[msg.author_id]['GameName']}#{UserRiotName[msg.author_id]['TagLine']}"
        )
    except EzAuthExp.AuthenticationError as result:
        _log.error(f"login AuthenticationError | Au:{msg.author_id} | {result}")
        text_sub = f"Make sure accont/password/verify-code correct\n`{result}`"
        cm = await get_card("登录错误，请检查账户/密码/邮箱验证码", text_sub, icon_cm.dont_do_that)
        await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
    except EzAuthExp.WaitOvertimeError as result:
        _log.error(f"login WaitOvertimeError | Au:{msg.author_id} | {result}")
        cm = await get_card("等待超时", "auth wait overtime", icon_cm.lagging)
        await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
    except EzAuthExp.RatelimitError as result:
        err_str = f"ERR! [{GetTime()}] login Au:{msg.author_id} - {result}"
        # 更新全局速率限制
        login_rate_limit = {'limit': True, 'time': time.time()}
        _log.error(err_str + " set login_rate_limit = True")
        # 这里是第一个出现速率限制err的用户,更新消息提示
        cm = await get_card(f"登录请求超速！请在{RATE_LIMITED_TIME}s后重试", "RatelimitError,try again later", icon_cm.lagging)
        await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
    except client_exceptions.ClientResponseError as result:
        err_str = f"ERR! [{GetTime()}] login Au:{msg.author_id}\n```\n{traceback.format_exc()}\n```\n"
        if 'auth.riotgames.com' and '403' in str(result):
            Login_Forbidden = True
            err_str += f"[Login] 403 err! set Login_Forbidden = True"
        elif '404' in str(result):
            err_str += f"[Login] 404 err! network err, try again"
        else:
            err_str += f"[Login] Unkown aiohttp ERR!"
        # 打印+发送消息
        _log.exception("Exception occur in login")
        await bot.client.send(debug_ch, err_str)
        cm = await get_card(err_str)
        await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
    except KeyError as result:
        _log.error(f"login | Au:{msg.author_id} | KeyError: {result}")
        text = f"遇到未知的KeyError，请[联系](https://kook.top/gpbTwZ)阿狸的主人哦~"
        text_sub = f"Unkown KeyError, please contact bot developer"
        if '0' in str(result):
            text = f"遇到不常见的KeyError，可能👊Api服务器炸了"
            text_sub = f"KeyError, maybe Roit API Offline"
        # 发送卡片消息
        cm = await get_card(text, text_sub, icon_cm.that_it)
        await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
    except requester.HTTPRequester.APIRequestFailed as result:  #卡片消息发送失败
        await BotLog.APIRequestFailed_Handler("login", traceback.format_exc(), msg, bot, cm, send_msg=send_msg)
    except Exception as result:  # 其他错误
        await BotLog.BaseException_Handler("login",
                                           traceback.format_exc(),
                                           msg,
                                           send_msg=send_msg,
                                           help="请加入帮助频道咨询，或尝试重新执行login命令")


@bot.command(name='tfa')
async def tfa_verify(msg: Message, tfa: str, *arg):
    _log.info(f"Au:{msg.author_id} {msg.author.username}#{msg.author.identify_num} | /tfa")
    if len(tfa) != 6:
        await msg.reply(f"邮箱验证码长度错误，请确认您输入了正确的6位验证码\n当前参数：`{tfa}`")
        return

    send_msg = {'msg_id': ''}
    try:
        # 1. 先判断用户是否在dict里面
        if msg.author_id not in UserAuthDict:
            await msg.reply("您不在UserAuthDict中，请先执行login！")
            return
        # 1.1 在，且auth对象是ezauth
        auth = UserAuthDict[msg.author_id]['auth']
        assert isinstance(auth, EzAuth)

        # 2.发送提示信息
        cm0 = await get_card(f"两步验证码「{tfa}」获取成功", "小憩一下，很快就好啦！", icon_cm.val_logo_gif)
        send_msg = await msg.reply(cm0)  #记录消息id用于后续更新

        # 3.进行邮箱验证
        res = await auth.email_verfiy(tfa)
        # 4.成功
        UserRiotName[msg.author_id] = {'auth_user_id': auth.user_id, 'GameName': auth.Name, 'TagLine': auth.Tag}
        text = f"登陆成功！欢迎回来，{UserRiotName[msg.author_id]['GameName']}#{UserRiotName[msg.author_id]['TagLine']}"
        info_text = "当前cookie有效期为2~3天，有任何问题请[点我](https://kook.top/gpbTwZ)"
        cm = await get_card(text, info_text, icon_cm.correct)
        await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)

    except EzAuthExp.MultifactorError as result:
        if "multifactor_attempt_failed" in str(result):
            cm = await get_card("两步验证码错误，请重试", str(result), icon_cm.lagging)
        else:
            cm = await get_card("邮箱验证错误，请重新login", str(result), icon_cm.lagging)
        # 更新消息
        await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
    except Exception as result:  # 其他错误
        await BotLog.BaseException_Handler("tfa", traceback.format_exc(), msg, help="请加入帮助频道咨询，或尝试重新执行login命令")


# 退出登录
@bot.command(name='logout')
async def logout(msg: Message, *arg):
    BotLog.logMsg(msg)
    try:
        global UserRiotName, UserAuthDict
        if msg.author_id not in UserAuthDict:  #使用not in判断是否不存在
            cm = await get_card("您尚未登陆！无须logout", "阿巴阿巴？", icon_cm.whats_that)
            await msg.reply(cm)
            return

        log_text = f"[Logout] Au:{msg.author_id} - {UserRiotName[msg.author_id]['GameName']}#{UserRiotName[msg.author_id]['TagLine']}"
        # 如果id存在，删除auth对象
        # 因为UserRiotName里面只存放了用户游戏名/uuid，且不作为是否登录的判断，所以不需要删除
        del UserAuthDict[msg.author_id]
        # 如果是vip用户，删除本地保存的cookie
        cookie_path = f"./log/cookie/{msg.author_id}.cke"
        # 判断路径是否存在，存在直接删除
        if os.path.exists(cookie_path):
            os.remove(cookie_path)  # 删除文件
            log_text += " - rm cookie file"

        text = f"已退出登录！下次再见，{UserRiotName[msg.author_id]['GameName']}#{UserRiotName[msg.author_id]['TagLine']}"
        cm = await get_card(text, "你会回来的，对吗？", icon_cm.crying_crab)
        await msg.reply(cm)
        _log.info(log_text)

    except Exception as result:  # 其他错误
        await BotLog.BaseException_Handler("logout", traceback.format_exc(), msg)


@bot.command(name='login-ap')
async def login_acpw(msg: Message, *arg):
    BotLog.logMsg(msg)
    try:
        if msg.author_id not in UserPwdReauth:
            await msg.reply(f"您没有保存账户密码或2fa用户，该命令无效")
            return
        send_text = 'none'
        if len(UserPwdReauth[msg.author_id]) == 0:
            send_text = "阿狸还没有用过您的账户密码来重新登录呢"
        else:
            send_text = '以下为账户密码登录日志\n'
            for i in UserPwdReauth[msg.author_id]:
                send_text += f"{i} - {UserPwdReauth[msg.author_id][i]}\n"
        # 发送信息
        await msg.reply(send_text)
    except Exception as result:  # 其他错误
        await BotLog.BaseException_Handler("login-ap", traceback.format_exc(), msg)


# cookie重新登录
async def login_reauth(kook_user_id: str):
    base_print = f"Au:{kook_user_id} | "
    _log.info(base_print + "auth_token failure,trying reauthorize()")
    global UserAuthDict, UserRiotName
    auth = UserAuthDict[kook_user_id]['auth']
    assert isinstance(auth, EzAuth)
    #用cookie重新登录,会返回一个bool是否成功
    ret = await auth.reauthorize()
    if ret:  #会返回一个bool是否成功,成功了重新赋值
        UserAuthDict[kook_user_id]['auth'] = auth
        _log.info(base_print + "reauthorize() Successful!")
    else:  # cookie重新登录失败
        _log.info(base_print + "reauthorize() Failed! T-T")  # 失败打印
        # 有保存账户密码+不是邮箱验证用户
        if kook_user_id in UserAuthDict['AP'] and (not UserAuthDict[kook_user_id]['2fa']):
            auth = EzAuth()  # 用账户密码重新登录
            resw = await auth.authorize(UserAuthDict['AP'][kook_user_id]['a'], UserAuthDict['AP'][kook_user_id]['p'])
            if not resw['status']:  # 需要邮箱验证，那就直接跳出
                _log.info(base_print + "authorize() need 2fa, return False")
                return False
            # 更新auth对象
            UserAuthDict[kook_user_id]['auth'] = auth
            auth.save_cookies(f"./log/cookie/{kook_user_id}.cke")  # 保存cookie
            # 记录使用账户密码重新登录的时间
            UserPwdReauth[kook_user_id][GetTime()] = UserRiotName[kook_user_id]['GameName']
            _log.info(base_print + "authflow() by AP")
            ret = True
    # 正好返回auth.reauthorize()的bool
    return ret


# 判断是否需要重新获取token
async def check_reauth(def_name: str = "", msg: Union[Message, str] = ''):
    """
    return value:
     - True: no need to reauthorize / get `user_id` as params & reauhorize success 
     - False: unkown err / reauthorize failed
     - send_msg(dict): get `Message` as params & reauhorize success
    """
    user_id = "[ERR!]"  #先给userid赋值，避免下方打印的时候报错（不出意外是会被下面的语句修改的）
    try:
        user_id = msg if isinstance(msg, str) else msg.author_id  #如果是str就直接用
        auth = UserAuthDict[user_id]['auth']
        assert isinstance(auth, EzAuth)
        # 直接从对象中获取user的Token
        riotUser = auth.get_riotuser_token()
        resp = await fetch_valorant_point(riotUser)
        # resp={'httpStatus': 400, 'errorCode': 'BAD_CLAIMS', 'message': 'Failure validating/decoding RSO Access Token'}
        # 如果没有这个键，会直接报错进except; 如果有这个键，就可以继续执行下面的内容
        test = resp['httpStatus']
        is_msg = isinstance(msg, Message)  #判断传入的类型是不是消息
        if is_msg:  #如果传入的是msg，则提示用户
            text = f"获取「{def_name}」失败！正在尝试重新获取token，您无需操作"
            cm = await get_card(text, f"{resp['message']}", icon_cm.im_good_phoniex)
            send_msg = await msg.reply(cm)

        # 不管传入的是用户id还是msg，都传userid进入该函数
        ret = await login_reauth(user_id)
        if ret == False and is_msg:  #没有正常返回,重新获取token失败
            text = f"重新获取token失败，请私聊「/login」重新登录\n"
            cm = await get_card(text, "Auto Reauthorize Failed!", icon_cm.crying_crab)
            await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
        elif ret == True and is_msg:  #正常重新登录，且传过来了消息
            return send_msg  #返回发送出去的消息（用于更新）

        return ret  #返回是否成功重登

    except client_exceptions.ClientResponseError as result:
        err_str = f"[Check_re_auth] aiohttp ERR!\n```\n{traceback.format_exc()}\n```\n"
        if 'auth.riotgames.com' and '403' in str(result):
            global Login_Forbidden
            Login_Forbidden = True
            err_str += f"[Check_re_auth] 403 err! set Login_Forbidden = True"
        elif '404' in str(result):
            err_str += f"[Check_re_auth] 404 err! network err, try again"
        else:
            err_str += f"[Check_re_auth] Unkown aiohttp ERR!"

        _log.error(err_str)
        await bot.client.send(debug_ch, err_str)
        return False
    # 用户在EzAuth初始化完毕之前调用了其他命令
    except EzAuthExp.InitError as result:
        _log.error(f"Au:{user_id} | EzAuth used before init")
        return False
    except Exception as result:
        if 'httpStatus' in str(result):
            _log.info(f"Au:{user_id} | No need to reauthorize [{result}]")
            return True
        else:
            _log.exception("Unkown Exception occur")
            await bot.client.send(debug_ch, f"[Check_re_auth] Unkown ERR!\n{traceback.format_exc()}")
            return False


# 计算当前时间和明天早上8点的差值
def shop_time_remain():
    today = datetime.today().strftime("%y-%m-%d %H:%M:%S")  #今天日期+时间
    tomorow = (datetime.today() + timedelta(days=1)).strftime("%y-%m-%d")  #明天日期
    times_tomorow = time.mktime(time.strptime(f"{tomorow} 08:00:00", "%y-%m-%d %H:%M:%S"))  #明天早上8点时间戳
    times_now = time.mktime(time.strptime(f"{today}", "%y-%m-%d %H:%M:%S"))  #现在的时间戳
    timeout = times_tomorow - times_now  #计算差值
    timeout = time.strftime("%H:%M:%S", time.gmtime(timeout))  #转换成可读时间
    return timeout


# 判断缓存好的图片是否可用
def is_CacheLatest(kook_user_id: str):
    # 判断vip用户是否在背景图中，且没有 切换登录用户/切换背景图
    is_Status = False
    if kook_user_id in VipShopBgDict['bg']:
        is_Status = VipShopBgDict['bg'][kook_user_id]['status']  # 如果有切换登录用户/背景图，此为false
    # 判断图片是不是今天的（可能出现早八提醒的时候出错，导致缓存没有更新，是昨天的图）
    if kook_user_id in VipShopBgDict['cache']:
        is_Today = (VipShopBgDict['cache'][kook_user_id]['cache_time'] - GetTimeStampOf8AM()) >= 0
        is_Cache = VipShopBgDict['cache'][kook_user_id]['cache_img'] != None
        return is_Today and is_Status and is_Cache  # 有一个为false，结果就是false
    else:  # 如果不在，初始化为none，时间戳为0
        VipShopBgDict['cache'][kook_user_id] = {'cache_time': 0, 'cache_img': None}
    return False


# 获取每日商店的命令
@bot.command(name='shop', aliases=['SHOP'])
async def get_daily_shop(msg: Message, *arg):
    BotLog.logMsg(msg)
    if arg != ():
        await msg.reply(f"`/shop`命令不需要参数。您是否想`/login`？")
        return
    elif Login_Forbidden:
        await Login_Forbidden_send(msg)
        return
    send_msg = None
    try:
        # 如果用户不在Authdict里面，代表没有登录，直接退出
        if msg.author_id not in UserAuthDict:
            cm = await get_card("您尚未登陆！请「私聊」使用login命令进行登录操作", f"「/login 账户 密码」请确认您知晓这是一个风险操作", icon_cm.whats_that)
            await msg.reply(cm)
            return

        reau = await check_reauth("每日商店", msg)
        if reau == False: return  #如果为假说明重新登录失败
        # 重新获取token成功，从dict中获取玩家id
        player_gamename = f"{UserRiotName[msg.author_id]['GameName']}#{UserRiotName[msg.author_id]['TagLine']}"
        # 获取玩家id成功了，再提示正在获取商店
        cm = await get_card("正在尝试获取您的每日商店", "阿狸正在施法，很快就好啦！", icon_cm.duck)
        if isinstance(reau, dict):  #如果传过来的是一个dict，说明重新登录成功且发送了消息
            await upd_card(reau['msg_id'], cm, channel_type=msg.channel_type)
            send_msg = reau
        else:
            send_msg = await msg.reply(cm)  #记录消息id用于后续更新

        # 计算获取每日商店要多久
        start = time.perf_counter()  #开始计时
        # 从auth的dict中获取对象
        auth = UserAuthDict[msg.author_id]['auth']
        assert isinstance(auth, EzAuth)
        riotUser = auth.get_riotuser_token()
        # 开始判断是否需要获取商店
        log_time = ""
        a_time = time.time()
        global UserShopCache, VipShopBgDict
        # UserShopCache["data"]每天早八会被清空，如果用户在里面且玩家id一样，那么说明已经获取过当日商店了
        if isClear_UserShopCache() and isSame_Authuuid(msg.author_id):  # 直接使用本地已有的当日商店
            list_shop = UserShopCache["data"][msg.author_id]["SkinsPanelLayout"]["SingleItemOffers"]  # 商店刷出来的4把枪
            timeout = shop_time_remain()  # 通过当前时间计算商店剩余时间
            log_time += f"[Dict_shop] {format(time.time()-a_time,'.4f')} "
        else:
            resp = await fetch_daily_shop(riotUser)  #本地没有，api获取每日商店
            list_shop = resp["SkinsPanelLayout"]["SingleItemOffers"]  # 商店刷出来的4把枪
            timeout = resp["SkinsPanelLayout"]["SingleItemOffersRemainingDurationInSeconds"]  # 剩余时间
            timeout = time.strftime("%H:%M:%S", time.gmtime(timeout))  # 将秒数转为标准时间
            # 需要设置uuid来保证是同一个用户，方便同日的下次查询
            UserShopCache["data"][msg.author_id] = {
                "auth_user_id":UserRiotName[msg.author_id]["auth_user_id"],
                "SkinsPanelLayout":resp["SkinsPanelLayout"]
            }
            log_time += f"[Api_shop] {format(time.time()-a_time,'.4f')} "

        # 开始画图
        draw_time = time.time()  #计算画图需要的时间
        is_vip = await BotVip.vip_ck(msg.author_id)  #判断用户是否为VIP
        img_ret = {'status': True, 'value': None}
        upload_flag = True
        # 初始化为一个展示错误的图片
        dailyshop_img_src = "https://img.kookapp.cn/assets/2023-02/5UxA8W06B70e803m.png"
        # 如果是vip而且path存在,背景图/登录用户没有更改过,图片缓存时间正确
        if is_vip and is_CacheLatest(msg.author_id):
            upload_flag = False  #有缓存图，直接使用本地已有链接
            dailyshop_img_src = VipShopBgDict['cache'][msg.author_id]['cache_img']
        elif is_vip:  # 本地缓存路径不存在，或者缓存过期
            play_currency = await fetch_vp_rp_dict(riotUser)  #获取用户的vp和rp
            # 如果没有设置背景图，那就设置为err
            background_img = ('err' if msg.author_id not in VipShopBgDict['bg'] else
                              VipShopBgDict['bg'][msg.author_id]["background"][0])
            img_ret = await ShopImg.get_shop_img_169(list_shop,
                                                     vp=play_currency['vp'],
                                                     rp=play_currency['rp'],
                                                     bg_img_src=background_img)
        else:  # 普通用户
            # 判断是否有缓存命中
            cache_ret = await ShopRate.query_ShopCache(skinlist=list_shop)
            if not cache_ret['status']:  # 缓存没有命中
                img_ret = await ShopImg.get_shop_img_11(list_shop)
            else:  # 命中
                upload_flag = False
                dailyshop_img_src = cache_ret['img_url']
                log_time += "[cache] "

        # img_ret 代表是否画图成功，如果是缓存命中，也当成功处理
        if img_ret['status']:
            bg = img_ret['value']  #获取图片
        else:  # 出现背景图片违规或其他问题
            await msg.reply(img_ret['value'])
            _log.info(f"[GetShopImg] Au:{msg.author_id} | {img_ret['value']}")
            return

        # 获取图片成功，打印画图耗时
        _log.info(log_time + f"- [Drawing] {format(time.time() - draw_time,'.4f')} - [Au] {msg.author_id}")
        # 判断是否需要上传，false不需要
        if upload_flag:
            # 上传图片
            imgByteArr = io.BytesIO()
            bg.save(imgByteArr, format='PNG')
            imgByte = imgByteArr.getvalue()
            dailyshop_img_src = await bot_upimg.client.create_asset(imgByte)  # type: ignore
            # 如果在bg里面代表有自定义背景图，需更新status
            if is_vip:
                if msg.author_id in VipShopBgDict['bg']:
                    VipShopBgDict['bg'][msg.author_id]['status'] = True
                # 设置商店图片缓存+图片缓存的时间
                VipShopBgDict['cache'][msg.author_id] = {'cache_img': dailyshop_img_src, 'cache_time': time.time()}
            else:  # 非vip，更新缓存
                await ShopRate.update_ShopCache(skinlist=list_shop, img_url=dailyshop_img_src)

        # 结束shop的总计时，结果为浮点数，保留两位小数
        shop_using_time = format(time.perf_counter() - start, '.2f')

        # 商店的图片 卡片
        cm = CardMessage()
        c = Card(color='#fb4b57')
        c.append(Module.Header(f"玩家 {player_gamename} 的每日商店！"))
        c.append(Module.Context(f"失效时间剩余: {timeout}    本次查询用时: {shop_using_time}s"))
        c.append(Module.Container(Element.Image(src=dailyshop_img_src)))
        cm.append(c)

        # 皮肤评分和评价卡片，用户不在rate_err_user里面才显示(在评论中发表违规言论的用户)
        if not check_rate_err_user(msg.author_id):
            cm = await ShopRate.get_shop_rate_cm(list_shop, msg.author_id, cm=cm)
            end = time.perf_counter()  #计算获取评分的时间
        # 更新消息
        await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
        # 结束，打印结果
        _log.info(f"Au:{msg.author_id} | daily_shop reply successful [{shop_using_time}/{format(end - start, '.2f')}]")
    except requester.HTTPRequester.APIRequestFailed as result:  #卡片消息发送失败
        await BotLog.APIRequestFailed_Handler("shop", traceback.format_exc(), msg, bot, cm, send_msg=send_msg)
    except Exception as result:
        err_str = f"ERR! [{GetTime()}] shop\n```\n{traceback.format_exc()}\n```\n"
        if "SkinsPanelLayout" in str(result):
            _log.error(err_str + resp)
            btext = f"KeyError:{result}, please re-login\n如果此问题重复出现，请[联系开发者](https://kook.top/gpbTwZ)"
            cm = await get_card(f"键值错误，需要重新登录", btext, icon_cm.whats_that)
            await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
        else:
            await BotLog.BaseException_Handler("shop", traceback.format_exc(), msg, send_msg=send_msg)


# 获取夜市
@bot.command(name='night', aliases=['NIGHT'])
async def get_night_market(msg: Message, *arg):
    BotLog.logMsg(msg)
    global NightMarketOff
    if arg != ():
        await msg.reply(f"`/night`命令不需要参数。您是否想`/login`？")
        return
    elif Login_Forbidden:
        await Login_Forbidden_send(msg)
        return
    elif NightMarketOff:
        await msg.reply(f"夜市暂未开放！请等开放了之后再使用本命令哦~")
        return

    send_msg = None
    try:
        if msg.author_id in UserAuthDict:
            reau = await check_reauth("夜市", msg)
            if reau == False: return  #如果为假说明重新登录失败

            # 重新获取token成功了再提示正在获取夜市
            cm0 = await get_card("正在尝试获取您的夜市", "阿狸正在施法，很快就好啦！", icon_cm.duck)
            if isinstance(reau, dict):  #如果传过来的是一个dict，说明重新登录成功且发送了消息
                await upd_card(reau['msg_id'], cm0, channel_type=msg.channel_type)
                send_msg = reau
            else:
                send_msg = await msg.reply(cm0)  #记录消息id用于后续更新

            #计算获取时间
            start = time.perf_counter()  #开始计时
            auth = UserAuthDict[msg.author_id]['auth']
            assert isinstance(auth, EzAuth)
            riotUser = auth.get_riotuser_token()
            # 获取商店（夜市是相同接口）
            resp = await fetch_daily_shop(riotUser)
            if "BonusStore" not in resp:  # 如果没有这个字段，说明夜市取消了
                NightMarketOff = False
                cm1 = await get_card("嗷~ 夜市已关闭 或 Api没能正确返回结果", "night_market closed! 'BonusStore' not in resp",
                                     icon_cm.duck)
                await upd_card(send_msg['msg_id'], cm1, channel_type=msg.channel_type)  # 更新消息
                _log.error("night_market closed! | 'BonusStore' not in resp")
                return

            timeout = resp["BonusStore"]["BonusStoreRemainingDurationInSeconds"]  #剩余时间
            timeout = time.strftime("%d %H:%M:%S", time.gmtime(timeout))  #将秒数转为标准时间

            cm = CardMessage()
            c = Card(color='#fb4b57')
            c.append(
                Module.Header(
                    f"玩家 {UserRiotName[msg.author_id]['GameName']}#{UserRiotName[msg.author_id]['TagLine']} 的夜市！"))
            for Bonus in resp["BonusStore"]["BonusStoreOffers"]:
                skin = fetch_skin_bylist(Bonus["Offer"]["OfferID"])
                skin_icon = skin["data"]['levels'][0]["displayIcon"]
                skin_name = skin["data"]["displayName"]
                for it in ValSkinList['data']:  #查找皮肤的等级
                    if it['levels'][0]['uuid'] == Bonus["Offer"]["OfferID"]:
                        res_iters = fetch_item_iters_bylist(it['contentTierUuid'])
                        break
                iter_emoji = ValItersEmoji[res_iters['data']['devName']]
                basePrice = Bonus["Offer"]["Cost"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"]  #原价
                discPercent = Bonus["DiscountPercent"]  # 打折百分比
                discPrice = Bonus["DiscountCosts"]["85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"]  #打折后的价格
                text = f"(emj){res_iters['data']['uuid']}(emj)[{iter_emoji}] {skin_name}\n"
                text += f"(emj)vp(emj)[3986996654014459/qGVLdavCfo03k03k] {discPrice} ~~{basePrice}~~ {discPercent}%Off"
                #c.append(Module.Section(Element.Text(text, Types.Text.KMD), Element.Image(src=skin_icon, size='sm')))
                c.append(Module.Section(Element.Text(text, Types.Text.KMD)))

            # 结束计时
            using_time = format(time.perf_counter() - start, '.2f')
            c.append(Module.Context(f"失效时间剩余: {timeout}    本次查询用时: {using_time}s"))
            cm.append(c)
            # 更新消息
            await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
            _log.info(f"Au:{msg.author_id} | night_market reply success [{using_time}]")
        else:
            cm = await get_card("您尚未登陆！请「私聊」使用login命令进行登录操作", f"「/login 账户 密码」请确认您知晓这是一个风险操作", icon_cm.whats_that)
            await msg.reply(cm)
            return

    except requester.HTTPRequester.APIRequestFailed as result:  #卡片消息发送失败
        await BotLog.APIRequestFailed_Handler("night", traceback.format_exc(), msg, bot, cm, send_msg=send_msg)
    except Exception as result:  # 其他错误
        await BotLog.BaseException_Handler("night", traceback.format_exc(), msg, send_msg=send_msg)


# 设置全局变量，打开/关闭夜市
@bot.command(name='open-nm')
async def open_night_market(msg: Message, *arg):
    BotLog.logMsg(msg)
    try:
        if msg.author_id == master_id:
            global NightMarketOff
            if NightMarketOff:
                NightMarketOff = False
            else:
                NightMarketOff = True

            await msg.reply(f"夜市状态修改！NightMarketOff: {NightMarketOff}")
        else:
            await msg.reply("您没有权限执行本命令！")
    except:
        err_str = f"ERR! [{GetTime()}] open-nm\n```\n{traceback.format_exc()}\n```"
        await msg.reply(f"{err_str}")
        _log.exception("Exception occur")


# 获取玩家卡面(添加point的别名)
@bot.command(name='uinfo', aliases=['point', 'UINFO', 'POINT'])
async def get_user_card(msg: Message, *arg):
    BotLog.logMsg(msg)
    if arg != ():
        await msg.reply(f"`/uinfo`命令不需要参数。您是否想`/login`？")
        return
    elif Login_Forbidden:
        await Login_Forbidden_send(msg)
        return
    send_msg = None
    try:
        if msg.author_id in UserAuthDict:
            reau = await check_reauth("玩家装备/通行证", msg)  #重新登录
            if reau == False: return  #如果为假说明重新登录失败

            cm = await get_card("正在尝试获取您的 玩家卡面/VP/R点", "阿狸正在施法，很快就好啦！", icon_cm.rgx_card)
            if isinstance(reau, dict):  #如果传过来的是一个dict，说明重新登录成功且发送了消息
                await upd_card(reau['msg_id'], cm, channel_type=msg.channel_type)
                send_msg = reau
            else:  # 如果不需要重新登录，则直接发消息
                send_msg = await msg.reply(cm)  #记录消息id用于后续更新

            auth = UserAuthDict[msg.author_id]['auth']
            assert isinstance(auth, EzAuth)
            riotUser = auth.get_riotuser_token()
            resp = await fetch_player_loadout(riotUser)  #获取玩家装备栏
            player_card = await fetch_playercard_uuid(resp['Identity']['PlayerCardID'])  #玩家卡面id
            player_title = await fetch_title_uuid(resp['Identity']['PlayerTitleID'])  #玩家称号id
            if 'data' not in player_card or player_card['status'] != 200:
                player_card = {'data': {'wideArt': 'https://img.kookapp.cn/assets/2022-09/PDlf7DcoUH0ck03k.png'}}
                _log.error(f"ERR![player_card] Au:{msg.author_id} uuid:{resp['Identity']['PlayerCardID']}")
            if 'data' not in player_title or player_title['status'] != 200:
                player_title = {
                    'data': {
                        "displayName": f"未知玩家卡面uuid！\nUnknow uuid: `{resp['Identity']['PlayerTitleID']}`"
                    }
                }
                _log.error(f"ERR![player_title] Au:{msg.author_id} uuid:{resp['Identity']['PlayerTitleID']}")
            # 可能遇到全新账户（没打过游戏）的情况
            if resp['Guns'] == None or resp['Sprays'] == None:
                cm = await get_card(f"状态错误！您是否登录了一个全新的账户？", f"card: `{player_card}`\ntitle: `{player_title}`",
                                    icon_cm.whats_that)
                await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
                return

            # 获取玩家等级
            resp = await fetch_player_level(riotUser)
            player_level = resp["Progress"]["Level"]  # 玩家等级
            player_level_xp = resp["Progress"]["XP"]  # 玩家等级经验值
            last_fwin = resp["LastTimeGrantedFirstWin"]  # 上次首胜时间
            next_fwin = resp["NextTimeFirstWinAvailable"]  # 下次首胜重置
            cm = CardMessage()
            c = Card(color='#fb4b57')
            c.append(
                Module.Header(
                    f"玩家 {UserRiotName[msg.author_id]['GameName']}#{UserRiotName[msg.author_id]['TagLine']} 的个人信息"))
            c.append(Module.Container(Element.Image(src=player_card['data']['wideArt'])))  #将图片插入进去
            text = f"玩家称号：" + player_title['data']['displayName'] + "\n"
            text += f"玩家等级：{player_level}  -  经验值：{player_level_xp}\n"
            text += f"上次首胜：{last_fwin}\n"
            text += f"首胜重置：{next_fwin}"
            c.append(Module.Section(Element.Text(text, Types.Text.KMD)))

            #获取玩家的vp和r点剩余的text
            resp = await fetch_vp_rp_dict(riotUser)
            text = f"(emj)r点(emj)[3986996654014459/X3cT7QzNsu03k03k] RP  {resp['rp']}    "
            text += f"(emj)vp(emj)[3986996654014459/qGVLdavCfo03k03k] VP  {resp['vp']}\n"
            c.append(Module.Section(Element.Text(text, Types.Text.KMD)))
            cm.append(c)
            await upd_card(send_msg['msg_id'], cm, channel_type=msg.channel_type)
            _log.info(f"Au:{msg.author_id} | uinfo reply successful!")

        else:
            cm = await get_card("您尚未登陆！请「私聊」使用login命令进行登录操作", f"「/login 账户 密码」请确认您知晓这是一个风险操作", icon_cm.whats_that)
            await msg.reply(cm)
            return

    except requester.HTTPRequester.APIRequestFailed as result:  #卡片消息发送失败
        await BotLog.APIRequestFailed_Handler("uinfo", traceback.format_exc(), msg, bot, cm, send_msg=send_msg)
    except Exception as result:
        err_str = f"ERR! [{GetTime()}] uinfo\n```\n{traceback.format_exc()}\n```"
        if "Identity" in str(result) or "Balances" in str(result):
            _log.exception("Exception occur")
            cm2 = await get_card(f"键值错误，需要重新登录", f"KeyError:{result}, please re-login", icon_cm.lagging)
            await upd_card(send_msg['msg_id'], cm2, channel_type=msg.channel_type)
        else:
            await BotLog.BaseException_Handler("uinfo", traceback.format_exc(), msg, send_msg=send_msg)


# 获取捆绑包信息(无需登录)
@bot.command(name='bundle', aliases=['skin'])
async def get_bundle(msg: Message, *arg):
    BotLog.logMsg(msg)
    if arg == ():
        await msg.reply(f"函数参数错误，name: `{arg}`\n")
        return
    try:
        name = " ".join(arg)  # 补全函数名
        name = zhconv.convert(name, 'zh-tw')  #将名字繁体化
        # 不能一来就在武器列表里面找，万一用户输入武器名，那就会把这个武器的所有皮肤都找出来，和该功能的需求不符合
        for b in ValBundleList:  #在本地查找
            if name in b['displayName']:
                # 确认在捆绑包里面有这个名字之后，在查找武器（这里不能使用displayName，因为有些捆绑包两个版本的名字不一样）
                weapenlist = await fetch_bundle_weapen_byname(name)
                cm = CardMessage()
                c = Card(Module.Section(Element.Text(f"已为您查询到 `{name}` 相关捆绑包", Types.Text.KMD)))
                for b in ValBundleList:
                    if name in b['displayName']:  # 将图片插入 卡片消息
                        c.append(Module.Container(Element.Image(src=b['displayIcon2'])))
                if weapenlist != []:  # 遇到“再来一局”这种旧皮肤捆绑包，找不到武器名字
                    text = "```\n"
                    for w in weapenlist:
                        res_price = fetch_item_price_bylist(w['lv_uuid'])
                        if res_price != None:  # 有可能出现返回值里面找不到这个皮肤的价格的情况，比如冠军套
                            price = res_price['Cost']['85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741']
                            text += '%-28s\t- vp%5s\n' % (w['displayName'], price)
                        else:  # 找不到价格就直接插入武器名字
                            text += f"{w['displayName']}\n"

                    text += "```\n"
                    c.append(Module.Section(Element.Text(text, Types.Text.KMD)))  #插入皮肤
                cm.append(c)
                await msg.reply(cm)
                _log.info(f"Au:{msg.author_id} | get_bundle reply successful!")
                return

        await msg.reply(f"未能查找到结果，请检查您的皮肤名拼写")
        _log.info(f"Au:{msg.author_id} | get_bundle failed! Can't find {name}")
    except Exception as result:
        err_str = f"ERR! [{GetTime()}] get_bundle\n```\n{traceback.format_exc()}\n```"
        _log.exception("Exception occur")
        await msg.reply(err_str)
        await bot.client.send(debug_ch, err_str)


# 设置rate的错误用户
@bot.command(name='ban-r')
async def set_rate_err_user(msg: Message, user_id: str):
    global SkinRateDict
    if msg.author_id != master_id:
        await msg.reply(f"您没有权限执行此命令！")
        return
    if user_id in SkinRateDict['err_user']:
        await msg.reply(f"该用户已在SkinRateDict['err_user']列表中")
    elif user_id in SkinRateDict['data']:
        for skin, info in SkinRateDict['data'][user_id].items():
            # 找到这条评论，将其删除
            if not await ShopRate.remove_UserRate(skin, user_id):
                await msg.reply(f"Au:{user_id} 删除 {skin} [{info['name']}] 错误")

        # 删除完该用户的所有评论之后，将其放入err_user
        temp_user = copy.deepcopy(SkinRateDict['data'][user_id])
        del SkinRateDict['data'][user_id]
        SkinRateDict['err_user'][user_id] = temp_user
        await msg.reply(f"用户 {user_id} 已被加入SkinRateDict['err_user']列表")
        _log.info(f"[rate_err_user] add Au:{user_id} | file save success")


# 每月1日删除用户
@bot.task.add_cron(day=1, timezone="Asia/Shanghai")
async def clear_rate_err_user():
    global SkinRateDict
    SkinRateDict['err_user'] = {}
    #写入文件
    SkinRateDict.save()
    _log.info(f"[BOT.TASK] clear_rate_err_user")


# 给一个皮肤评分（灵感来自微信小程序”瓦的小卖铺“）
@bot.command(name="rate", aliases=['评分'])
async def rate_skin_add(msg: Message, *arg):
    BotLog.logMsg(msg)
    if check_rate_err_user(msg.author_id):
        await msg.reply(f"您有过不良评论记录，阿狸现已不允许您使用相关功能\n后台存放了所有用户的评论内容和评论时间。在此提醒，请不要在评论的时候发送不雅言论！")
        return
    elif arg == ():
        await msg.reply(f"你没有提供皮肤参数！skin: `{arg}`\n正确用法：`/rate 您想评价的皮肤名`")
        return
    try:
        name = " ".join(arg)
        retlist = await ShopRate.get_available_skinlist(name)
        if retlist == []:  # 空list，有问题
            await msg.reply(f"该皮肤不在列表中[或没有价格]，请重新查询！")
            return

        # 将皮肤list插入到选择列表中，用户使用/rts命令选择
        UserRtsDict[msg.author_id] = retlist
        # 获取选择列表的text
        ret = await ShopRate.get_skinlist_rate_text(retlist, msg.author_id)
        text = f"```\n{ret['text']}```"

        cm = CardMessage()
        c = Card(Module.Header(f"查询到 {name} 相关皮肤如下"), Module.Section(Element.Text(text, Types.Text.KMD)),
                 Module.Section(Element.Text("请使用以下命令对皮肤进行评分;\n√代表您已评价过该皮肤，+已有玩家评价，-无人评价\n", Types.Text.KMD)))
        text1 = "```\n/rts 序号 评分 吐槽\n"
        text1 += "序号：上面列表中的皮肤序号\n"
        text1 += "评分：给皮肤打分，范围0~100\n"
        text1 += "吐槽：说说你对这个皮肤的看法\n"
        text1 += "吐槽的时候请注意文明用语！\n```\n"
        text1 += f"您已经评价过了 {ret['sum']} 个皮肤"
        c.append(Module.Section(Element.Text(text1, Types.Text.KMD)))
        cm.append(c)
        await msg.reply(cm)

    except requester.HTTPRequester.APIRequestFailed as result:  #卡片消息发送失败
        await BotLog.APIRequestFailed_Handler("rate", traceback.format_exc(), msg, bot, cm)
    except Exception as result:  # 其他错误
        await BotLog.BaseException_Handler("rate", traceback.format_exc(), msg)


#选择皮肤（这个命令必须跟着上面的命令用）
@bot.command(name="rts")
async def rate_skin_select(msg: Message, index: str = "err", rating: str = "err", *arg):
    BotLog.logMsg(msg)
    if check_rate_err_user(msg.author_id):
        await msg.reply(f"您有过不良评论记录，阿狸现已不允许您使用相关功能\n后台存放了所有用户的评论内容和评论时间。在此提醒，请不要在评论的时候发送不雅言论！")
        return
    elif index == "err" or '-' in index:
        await msg.reply(f"参数不正确！请正确选择您需要评分的皮肤序号\n正确用法：`/rts 序号 评分 吐槽`")
        return
    elif rating == "err" or '-' in rating:
        await msg.reply(f"参数不正确！请正确提供您给该皮肤的打分，范围0~100\n正确用法：`/rts 序号 评分 吐槽`")
        return
    elif arg == ():
        await msg.reply(f"您似乎没有评论此皮肤呢，多少说点什么吧~\n正确用法：`/rts 序号 评分 吐槽`")
        return
    try:
        if msg.author_id in UserRtsDict:
            _index = int(index)  #转成int下标（不能处理负数）
            _rating = int(rating)  #转成分数
            if _index >= len(UserRtsDict[msg.author_id]):  #下标判断，避免越界
                await msg.reply(f"您的选择越界了！请正确填写序号")
                return
            elif _rating < 0 or _rating > 100:
                await msg.reply(f"您的评分有误，正确范围为0~100")
                return

            S_skin = UserRtsDict[msg.author_id][_index]
            skin_uuid = S_skin['skin']['lv_uuid']
            comment = " ".join(arg)  #用户对此皮肤的评论
            point = _rating  # 初始化分数
            text1 = ""
            text2 = ""
            # 先从leancloud获取该皮肤的分数
            skin_rate = await ShopRate.query_SkinRate(skin_uuid)
            if skin_rate['status']:  # 找到了
                #用户的评分和皮肤平均分差值不能超过32，避免有人乱刷分
                if abs(float(_rating) - skin_rate['rating']) <= 32:
                    # 计算分数
                    point = (skin_rate['rating'] + float(_rating)) / 2
                else:  # 差值过大，不计入皮肤平均值
                    point = skin_rate['rating']
                    text2 += f"由于您的评分和皮肤平均分差值大于32，所以您的评分不会计入皮肤平均分，但您的评论会进行保留\n"

            # 更新数据库中皮肤评分
            await ShopRate.update_SkinRate(skin_uuid, S_skin['skin']['displayName'], point)
            # 用户之前没有评价过，新建键值
            if msg.author_id not in SkinRateDict['data']:
                SkinRateDict['data'][msg.author_id] = {}
            # 设置uuid的键值
            SkinRateDict['data'][msg.author_id][skin_uuid] = {}
            SkinRateDict['data'][msg.author_id][skin_uuid]['name'] = S_skin['skin']['displayName']
            SkinRateDict['data'][msg.author_id][skin_uuid]['cmt'] = comment
            SkinRateDict['data'][msg.author_id][skin_uuid]['rating'] = point
            SkinRateDict['data'][msg.author_id][skin_uuid]['time'] = int(time.time())  # 秒级
            SkinRateDict['data'][msg.author_id][skin_uuid]['msg_id'] = msg.id
            # 数据库添加该评论
            await ShopRate.update_UserRate(skin_uuid, SkinRateDict['data'][msg.author_id][skin_uuid], msg.author_id)
            # 更新用户已评价的皮肤
            await ShopRate.update_UserCmt(msg.author_id, skin_uuid)

            text1 += f"评价成功！{S_skin['skin']['displayName']}"
            text2 += f"您的评分：{_rating}\n"
            text2 += f"皮肤平均分：{point}\n"
            text2 += f"您的评语：{comment}"
            cm = CardMessage()
            c = Card(Module.Header(text1), Module.Divider(), Module.Section(Element.Text(text2, Types.Text.KMD)))
            cm.append(c)
            # 设置成功并删除list后，再发送提醒事项设置成功的消息
            await msg.reply(cm)
            _log.info(f"[rts] Au:{msg.author_id} | {text1} {skin_uuid}")
        else:
            await msg.reply(f"您需要执行 `/rate 皮肤名` 来查找皮肤\n再使用 `/rts` 进行选择")

    except requester.HTTPRequester.APIRequestFailed as result:  #卡片消息发送失败
        await BotLog.APIRequestFailed_Handler("rts", traceback.format_exc(), msg, bot, cm)
    except Exception as result:  # 其他错误
        await BotLog.BaseException_Handler("rts", traceback.format_exc(), msg)


# 查看昨日牛人/屌丝
@bot.command(name="kkn")
async def show_shoprate(msg: Message):
    BotLog.logMsg(msg)
    if check_rate_err_user(msg.author_id):
        await msg.reply(f"您有过不良评论记录，阿狸现已不允许您使用相关功能\n后台存放了所有用户的评论内容和评论时间。在此提醒，请不要在评论的时候发送不雅言论！")
        return
    try:
        # 从数据库中获取
        cmpRet = await ShopRate.get_ShopCmp()
        if not cmpRet['status']:
            await msg.reply(f"获取昨日天选之子和丐帮帮主出错！请重试或联系开发者")
            return

        cm = CardMessage()
        c = Card(Module.Header(f"来看看昨日天选之子和丐帮帮主吧！"), Module.Divider())
        # best
        text = ""
        c.append(Module.Section(Element.Text(f"**天选之子** 综合评分 {cmpRet['best']['rating']}", Types.Text.KMD)))
        c.append(Module.Context(f"来自 {cmpRet['best']['platform']} 平台"))
        for sk in cmpRet['best']['skin_list']:
            # 数据库中获取一个皮肤的评分情况
            skinRet = await ShopRate.query_SkinRate(sk)
            if skinRet['status']:
                skin_name = f"「{skinRet['skin_name']}」"
                text += f"%-50s\t\t评分: {skinRet['rating']}\n" % skin_name
        c.append(Module.Section(Element.Text(text, Types.Text.KMD)))
        c.append(Module.Divider())
        # worse
        text = ""
        c.append(Module.Section(Element.Text(f"**丐帮帮主** 综合评分 {cmpRet['worse']['rating']}", Types.Text.KMD)))
        c.append(Module.Context(f"来自 {cmpRet['worse']['platform']} 平台"))
        for sk in cmpRet['worse']['skin_list']:
            # 数据库中获取一个皮肤的评分情况
            skinRet = await ShopRate.query_SkinRate(sk)
            if skinRet['status']:
                skin_name = f"「{skinRet['skin_name']}」"
                text += f"%-50s\t\t评分: {skinRet['rating']}\n" % skin_name
        c.append(Module.Section(Element.Text(text, Types.Text.KMD)))
        cm.append(c)
        await msg.reply(cm)

        _log.info(f"[kkn] Au:{msg.author_id} | reply success")
    except requester.HTTPRequester.APIRequestFailed as result:  #卡片消息发送失败
        await BotLog.APIRequestFailed_Handler("rts", traceback.format_exc(), msg, bot, cm)
    except Exception as result:  # 其他错误
        await BotLog.BaseException_Handler("rts", traceback.format_exc(), msg)


# 检查用户是否在错误用户里面
async def check_notify_err_user(msg: Message):
    """Return(bool):
     - True: user in SkinNotifyDict['err_user']
     - False: user not in, everythings is good
    """
    global SkinNotifyDict
    if msg.author_id in SkinNotifyDict['err_user']:
        try:
            user = await bot.client.fetch_user(msg.author_id)
            await user.send(f"这是一个私聊测试，请忽略此条消息")  #先测试是否能发私聊
            # 可以发起，在err_user列表中删除该用户
            del SkinNotifyDict['err_user'][msg.author_id]
            return False
        except:
            err_cur = str(traceback.format_exc())
            err_str = f"ERR![{GetTime()}] err_Au:{msg.author_id} user.send\n```\n{err_cur}\n```"
            if '屏蔽' in err_cur or '无法发起' in err_cur:
                await msg.reply(f"您之前屏蔽了阿狸，或阿狸无法向您发起私信\n您的皮肤提醒信息已经被`删除`，请在解除对阿狸的屏蔽后重新操作！\n{err_str}")
            else:
                err_str += "\n如果此错误多次出现，请[联系](https://kook.top/gpbTwZ)开发者"
                await msg.reply(err_str)
            # 不管出现什么错误，都返回True代表无法私信
            return True
    else:
        return False


#设置提醒（出现xx皮肤）
@bot.command(name="notify-add", aliases=['notify-a'])
async def add_skin_notify(msg: Message, *arg):
    BotLog.logMsg(msg)
    if arg == ():
        await msg.reply(f"你没有提供皮肤参数！skin: `{arg}`")
        return
    try:
        if await check_notify_err_user(msg):
            return
        # 检查用户的提醒栏位
        vip_status = await BotVip.vip_ck(msg.author_id)
        if msg.author_id in SkinNotifyDict['data'] and not vip_status:
            if len(SkinNotifyDict['data'][msg.author_id]) > NOTIFY_NUM:
                cm = await get_card(f"您的皮肤提醒栏位已满", f"想解锁更多栏位，可以来[支持一下](https://afdian.net/a/128ahri?tab=shop)阿狸呢！",
                                    icon_cm.rgx_broken)
                await msg.reply(cm)
                return

        #用户没有登录
        if msg.author_id not in UserAuthDict:
            cm = await get_card("您尚未登陆！请「私聊」使用login命令进行登录操作", f"「/login 账户 密码」请确认您知晓这是一个风险操作", icon_cm.whats_that)
            await msg.reply(cm)
            return

        name = " ".join(arg)
        name = zhconv.convert(name, 'zh-tw')  #将名字繁体化
        sklist = fetch_skin_list_byname(name)
        if sklist == []:  #空list代表这个皮肤不在里面
            await msg.reply(f"该皮肤不在列表中，请重新查询！")
            return

        retlist = list()  #用于返回的list，因为不是所有搜到的皮肤都有价格，没有价格的皮肤就是商店不刷的
        for s in sklist:
            res_price = fetch_item_price_bylist(s['lv_uuid'])
            if res_price != None:  # 有可能出现返回值里面找不到这个皮肤的价格的情况，比如冠军套
                price = res_price['Cost']['85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741']
                data = {'skin': s, 'price': price}
                retlist.append(data)

        if retlist == []:  #空list代表这个皮肤没有价格
            await msg.reply(f"该皮肤不在列表中 [没有价格]，请重新查询！")
            return

        UserStsDict[msg.author_id] = retlist
        i = 0
        text = "```\n"  #模拟一个选择表
        for w in retlist:
            text += f"[{i}] - {w['skin']['displayName']}  - VP {w['price']}\n"
            i += 1
        text += "```"
        cm = CardMessage()
        c = Card(Module.Header(f"查询到 {name} 相关皮肤如下"),
                 Module.Context(Element.Text("请在下方键入序号进行选择，请不要选择已购买的皮肤", Types.Text.KMD)),
                 Module.Section(Element.Text(text + "\n\n使用 `/sts 序号` 来选择", Types.Text.KMD)))
        cm.append(c)
        await msg.reply(cm)

    except Exception as result:  # 其他错误
        await BotLog.BaseException_Handler("notify-add", traceback.format_exc(), msg)


#选择皮肤（这个命令必须跟着上面的命令用）
@bot.command(name="sts")
async def select_skin_notify(msg: Message, n: str = "err", *arg):
    BotLog.logMsg(msg)
    if n == "err" or '-' in n:
        await msg.reply(f"参数不正确！请选择您需要提醒的皮肤序号")
        return
    try:
        global SkinNotifyDict
        if msg.author_id in UserStsDict:
            num = int(n)  #转成int下标（不能处理负数）
            if num >= len(UserStsDict[msg.author_id]):  #下标判断，避免越界
                await msg.reply(f"您的选择越界了！请正确填写序号")
                return

            # 先发送一个私聊消息，作为测试（避免有人开了不给私信）
            user_test = await bot.client.fetch_user(msg.author_id)
            await user_test.send(f"这是一个私信测试。请不要修改您的私信权限，以免notify功能无法正常使用")
            # 测试通过，继续后续插入
            S_skin = UserStsDict[msg.author_id][num]
            if msg.author_id not in SkinNotifyDict['data']:
                SkinNotifyDict['data'][msg.author_id] = {}
                SkinNotifyDict['data'][msg.author_id][S_skin['skin']['lv_uuid']] = S_skin['skin']['displayName']
            else:  #如果存在了就直接在后面添加
                SkinNotifyDict['data'][msg.author_id][S_skin['skin']['lv_uuid']] = S_skin['skin']['displayName']
            _log.debug(SkinNotifyDict['data'][msg.author_id])

            del UserStsDict[msg.author_id]  #删除选择页面中的list
            text = f"设置成功！已开启`{S_skin['skin']['displayName']}`的提醒"
            # 设置成功并删除list后，再发送提醒事项设置成功的消息
            await msg.reply(text)
            _log.info(f"[sts] Au:{msg.author_id} | {text}")
        else:
            await msg.reply(f"您需要（重新）执行 `/notify-a` 来设置提醒皮肤")
    except requester.HTTPRequester.APIRequestFailed as result:  #消息发送失败
        err_str = f"ERR! [{GetTime()}] sts\n```\n{traceback.format_exc()}\n```\n"
        await bot.client.send(debug_ch, err_str)
        await BotLog.APIRequestFailed_Handler("sts", traceback.format_exc(), msg, bot)
    except Exception as result:  # 其他错误
        await BotLog.BaseException_Handler("sts", traceback.format_exc(), msg)


# 显示当前设置好了的皮肤通知
@bot.command(name="notify-list", aliases=['notify-l'])
async def list_skin_notify(msg: Message, *arg):
    BotLog.logMsg(msg)
    try:
        if await check_notify_err_user(msg):
            return
        if msg.author_id in SkinNotifyDict['data']:
            text = "```\n"
            for skin, name in SkinNotifyDict['data'][msg.author_id].items():
                text += skin + ' = ' + name + '\n'
            text += "```\n"
            text += "如果您需要添加皮肤，请使用`notify-a 皮肤名`\n"
            text += "如果您需要删除皮肤，请使用`notify-d uuid`\n"
            text += "注：`=`号前面很长的那一串就是uuid\n"
            await msg.reply(text)
    except Exception as result:
        await BotLog.BaseException_Handler("notify-list", traceback.format_exc(), msg, debug_send=debug_ch)


# 删除已有皮肤通知
@bot.command(name="notify-del", aliases=['notify-d'])
async def delete_skin_notify(msg: Message, uuid: str = "err", *arg):
    BotLog.logMsg(msg)
    if uuid == 'err':
        await msg.reply(f"请提供正确的皮肤uuid：`{uuid}`")
        return
    try:
        if await check_notify_err_user(msg):
            return
        global SkinNotifyDict
        if msg.author_id in SkinNotifyDict['data']:
            if uuid in SkinNotifyDict['data'][msg.author_id]:
                _log.info(f"notify-d | Au:{msg.author_id} | {uuid} {SkinNotifyDict['data'][msg.author_id][uuid]}")
                await msg.reply(f"已删除皮肤：`{SkinNotifyDict['data'][msg.author_id][uuid]}`")
                del SkinNotifyDict['data'][msg.author_id][uuid]
            else:
                await msg.reply(f"您提供的uuid不在列表中！")
                return
    except Exception as result:
        await BotLog.BaseException_Handler("notify-del", traceback.format_exc(), msg, debug_send=debug_ch)


#独立函数，为了封装成命令+定时
async def auto_skin_notify():
    global SkinNotifyDict, SkinRateDict, UserShopCache, VipShopBgDict
    try:
        _log.info(f"[BOT.TASK.NOTIFY] Start")  #开始的时候打印一下
        UserShopCache["data"] = {}  # 清空用户的商店
        UserShopCache["clear_time"] = time.time() # 更新时间
        #清空昨日最好/最差用户的皮肤表
        SkinRateDict["kkn"] = copy.deepcopy(SkinRateDict["cmp"])
        SkinRateDict["cmp"]["best"]["list_shop"] = list()
        SkinRateDict["cmp"]["best"]["rating"] = 0
        SkinRateDict["cmp"]["worse"]["list_shop"] = list()
        SkinRateDict["cmp"]["worse"]["rating"] = 100
        # 更新数据库中的记录，并重置计数器
        await ShopRate.update_ShopCmp(SkinRateDict["kkn"]["best"], SkinRateDict["kkn"]["worse"], 'kook', True)
        _log.info(f"[BOT.TASK.NOTIFY] SkinRateDict/UserShopCache clear, sleep(10)")
        #睡10s再开始遍历（避免时间不准）
        await asyncio.sleep(10)
        _log.info(f"[BOT.TASK.NOTIFY] skin_notify Start")
        #加载vip用户列表
        VipUserD = copy.deepcopy(VipUserDict)
        err_count = 0  # 设置一个count来计算出错的用户数量
        log_vip_failed = f"[BOT.TASK.NOTIFY] reauthorize failed  = VAu: "
        log_vip_not_login = f"[BOT.TASK.NOTIFY] not_in UserAuthDict = VAu: "
        #先遍历vip用户列表，获取vip用户的商店
        for vip, uinfo in VipUserD.items():
            try:
                user = await bot.client.fetch_user(vip)
                if vip in UserAuthDict:
                    if await check_reauth("定时获取玩家商店", vip) == True:  # 重新登录,如果为假说明重新登录失败
                        shop_text = "err"
                        start = time.perf_counter()  #开始计时
                        auth = UserAuthDict[vip]['auth']
                        assert isinstance(auth, EzAuth)
                        riotUser = auth.get_riotuser_token()
                        a_time = time.time()  # 获取token的时间
                        resp = await fetch_daily_shop(riotUser)  # 获取每日商店

                        # 判断夜市有没有开，只会判断一次
                        global NightMarketOff  #true代表夜市没有开启
                        if NightMarketOff and "BonusStore" in resp:  #夜市字段存在
                            NightMarketOff = False  #夜市开启！

                        list_shop = resp["SkinsPanelLayout"]["SingleItemOffers"]  # 商店刷出来的4把枪
                        timeout = resp["SkinsPanelLayout"]["SingleItemOffersRemainingDurationInSeconds"]  #剩余时间
                        timeout = time.strftime("%H:%M:%S", time.gmtime(timeout))  #将秒数转为标准时间
                        log_time = f"[Api_shop] {format(time.time()-a_time,'.4f')} "
                        await ShopRate.check_shop_rate(vip, list_shop)  #计算用户商店得分
                        #vip用户会提前缓存当日商店，需要设置uuid来保证是同一个游戏用户
                        UserShopCache["data"][vip] = {}
                        UserShopCache["data"][vip]["auth_user_id"] = UserRiotName[vip]["auth_user_id"]
                        UserShopCache["data"][vip]["SkinsPanelLayout"] = resp["SkinsPanelLayout"]
                        #直接获取商店图片
                        draw_time = time.time()  #开始计算画图需要的时间
                        img_shop_path = f"./log/img_temp_vip/shop/{vip}.png"
                        play_currency = await fetch_vp_rp_dict(riotUser)  #获取用户的vp和rp
                        # 设置用户背景图，如果在则用，否则返回err
                        background_img = ('err' if vip not in VipShopBgDict['bg'] else
                                          VipShopBgDict['bg'][vip]["background"][0])
                        img_ret = await ShopImg.get_shop_img_169(list_shop,
                                                                 vp=play_currency['vp'],
                                                                 rp=play_currency['rp'],
                                                                 bg_img_src=background_img)
                        if img_ret['status']:
                            bg_shop = img_ret['value']
                            bg_shop.save(img_shop_path, format='PNG')
                            # 打印画图日志
                            log_time += f"- [Drawing] {format(time.time() - draw_time,'.4f')}  - [Au] {vip}"
                            _log.info(log_time)
                            dailyshop_img_src = await bot_upimg.client.create_asset(img_shop_path)  # 上传图片
                            VipShopBgDict['cache'][vip] = {
                                'cache_img': dailyshop_img_src,
                                'cache_time': time.time()
                            }  # 缓存图片的url+设置图片缓存的时间
                            if vip in VipShopBgDict['bg']: VipShopBgDict['bg'][vip]['status'] = True
                        else:  #如果图片没有正常返回，那就发送文字版本
                            shop_text = ""
                            for skinuuid in list_shop:
                                res_item = fetch_skin_bylist(skinuuid)  # 从本地文件中查找
                                res_price = fetch_item_price_bylist(skinuuid)  # 在本地文件中查找
                                price = res_price['Cost']['85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741']
                                shop_text += f"{res_item['data']['displayName']}     - VP {price}\n"
                            _log.info(f"[BOT.TASK.NOTIFY] VAu:{vip} | test img err, using text")

                        # 结束shop的总计时 结果为浮点数，保留两位小数
                        using_time = format(time.perf_counter() - start, '.2f')
                        #卡片消息发送图片或者text
                        cm = CardMessage()
                        c = Card(color='#fb4b57')
                        if shop_text == "err":
                            c.append(
                                Module.Header(
                                    f"早安！玩家 {UserRiotName[vip]['GameName']}#{UserRiotName[vip]['TagLine']} 的每日商店"))
                            c.append(Module.Context(f"失效时间剩余: {timeout}    本次查询用时: {using_time}s"))
                            c.append(Module.Container(Element.Image(src=dailyshop_img_src)))
                        else:
                            c.append(
                                Module.Section(
                                    Element.Text(
                                        f"早安！玩家 {UserRiotName[vip]['GameName']}#{UserRiotName[vip]['TagLine']}",
                                        Types.Text.KMD), Element.Image(src=icon_cm.shot_on_fire, size='sm')))
                            c.append(Module.Section(Element.Text(shop_text, Types.Text.KMD)))
                            c.append(Module.Context(Element.Text(f"这里有没有你想要的枪皮呢？", Types.Text.KMD)))
                        # 发送
                        cm.append(c)
                        await user.send(cm)
                        _log.info(f"[BOT.TASK.NOTIFY] VAu:{vip} | notify_shop success [{using_time}]")
                    else:  #reauthorize failed!
                        log_vip_failed += f"({vip})"
                else:  #不在auth里面说明没有登录
                    log_vip_not_login += f"({vip})"
            except Exception as result:  #这个是用来获取单个用户的问题的
                err_cur = str(traceback.format_exc())
                err_str = f"ERR![BOT.TASK.NOTIFY] VAu:{vip} vip_user.send\n```\n{err_cur}\n```"
                _log.error(err_str)
                err_count += 1
                if '屏蔽' in err_cur or '无法发起' in err_cur:
                    SkinNotifyDict['err_user'][vip] = GetTime()
                    err_str += f"\nadd to ['err_user']"

                await bot.client.send(debug_ch, err_str)  #发送消息到debug频道
        #打印vip的log信息
        _log.info(log_vip_failed)
        _log.info(log_vip_not_login)

        # 再遍历所有用户的皮肤提醒
        log_failed = f"[BOT.TASK.NOTIFY] reauthorize failed  = Au: "
        log_not_login = f"[BOT.TASK.NOTIFY] not_in UserAuthDict = Au: "
        temp_SkinNotifyDict = copy.deepcopy(SkinNotifyDict)
        for aid, skin in temp_SkinNotifyDict['data'].items():
            try:
                user = await bot.client.fetch_user(aid)
                if aid in UserAuthDict:
                    if await check_reauth("定时获取玩家商店", aid) == True:  # 重新登录,如果为假说明重新登录失败
                        auth = UserAuthDict[aid]['auth']
                        assert isinstance(auth, EzAuth)
                        riotUser = auth.get_riotuser_token()
                        #vip用户在前面已经获取过商店了
                        if await BotVip.vip_ck(aid):
                            list_shop = UserShopCache["data"][aid]["SkinsPanelLayout"]["SingleItemOffers"]
                        else:
                            resp = await fetch_daily_shop(riotUser)  # 获取每日商店
                            list_shop = resp["SkinsPanelLayout"]["SingleItemOffers"]  # 商店刷出来的4把枪
                            await ShopRate.check_shop_rate(vip, list_shop)  #计算非vip用户商店得分

                        # 然后再遍历列表查看是否有提醒皮肤
                        # 关于下面这一行参考 https://img.kookapp.cn/assets/2022-08/oYbf8PM6Z70ae04s.png
                        target_skin = [val for key, val in skin.items() if key in list_shop]
                        for name in target_skin:
                            _log.info(f"[BOT.TASK.NOTIFY] Au:{aid} auto_skin_notify = {name}")
                            await user.send(f"[{GetTime()}] 您的每日商店刷出`{name}`了，请上号查看哦！")
                        # 打印这个说明这个用户正常遍历完了
                        _log.info(f"[BOT.TASK.NOTIFY] Au:{aid} auto_skin_notify = None")
                    else:  #reauthorize failed!
                        log_failed += f"({aid})"
                else:  #不在auth里面说明没有登录
                    log_not_login += f"({aid})"
            except Exception as result:  #这个是用来获取单个用户的问题的
                err_cur = str(traceback.format_exc())
                err_str = f"ERR![BOT.TASK.NOTIFY] Au:{aid} user.send\n```\n{err_cur}\n```"
                err_count += 1
                if '屏蔽' in err_cur or '无法发起' in err_cur:
                    del SkinNotifyDict['data'][aid]  #直接粗暴解决，删除用户
                    SkinNotifyDict['err_user'][aid] = GetTime()
                    err_str += f"\ndel SkinNotifyDict['data'][{aid}],add to ['err_user']"

                _log.error(err_str)
                await bot.client.send(debug_ch, err_str)  # 发送消息到debug频道

        #打印普通用户的log信息
        _log.info(log_failed)
        _log.info(log_not_login)
        #完成遍历后，如果有删除才重新保存dict
        if temp_SkinNotifyDict != SkinNotifyDict:
            SkinNotifyDict.save()
            _log.info("[BOT.TASK.NOTIFY] save SkinNotifyDict")

        # 打印结束信息
        finish_str = f"[BOT.TASK.NOTIFY] Finish at {GetTime()} [ERR {err_count}]"
        _log.info(finish_str)  #正常完成
        await bot.client.send(debug_ch, finish_str)  #发送消息到debug频道
    except Exception as result:
        err_str = f"ERR! [{GetTime()}] auto_skin_notify\n```\n{traceback.format_exc()}\n```"
        _log.exception("Exception occur")
        await bot.client.send(debug_ch, err_str)  # 发送消息到debug频道


@bot.task.add_cron(hour=8, minute=0, timezone="Asia/Shanghai")
async def auto_skin_notify_task():
    await auto_skin_notify()


# 手动执行notify task
@bot.command(name='notify-test')
async def auto_skin_notify_cmd(msg: Message, *arg):
    BotLog.logMsg(msg)
    if msg.author_id == master_id:
        await auto_skin_notify()


# 手动更新商店物品和价格
@bot.command(name='update_spb', aliases=['update', 'upd'])
async def update_skin_price_bundle(msg: Message):
    BotLog.logMsg(msg)
    try:
        if msg.author_id == master_id:
            if await ValFileUpd.update_skins(msg):
                await msg.reply(f"成功更新：商店皮肤")
            if await ValFileUpd.update_bundle_url(msg, bot_upimg):
                await msg.reply(f"成功更新：捆绑包")
            # 获取物品价格需要登录
            auth = UserAuthDict[msg.author_id]['auth']
            assert isinstance(auth, EzAuth)
            riotUser = auth.get_riotuser_token()
            if await ValFileUpd.update_price(msg, riotUser):
                await msg.reply(f"成功更新：物品价格")
    except Exception as result:
        _log.exception("Exception occur")
        await msg.reply(f"ERR! [{GetTime()}] update_spb\n```\n{traceback.format_exc()}\n```")


#######################################################################################################
#######################################################################################################


# 显示当前阿狸加入了多少个服务器，以及用户数量
@bot.command(name='log-list', aliases=['log-l', 'log'])
async def bot_log_list(msg: Message, *arg):
    BotLog.logMsg(msg)
    try:
        if msg.author_id == master_id:
            retDict = await BotLog.log_bot_list(msg)  # 获取用户/服务器列表
            res_text = await BotLog.log_bot_list_text(retDict)  # 获取text

            cm = CardMessage()
            c = Card(
                Module.Header(f"来看看阿狸当前的用户记录吧！"),
                Module.Context(
                    f"服务器总数: {retDict['guild']['guild_total']}  活跃服务器: {retDict['guild']['guild_active']}  用户数: {retDict['user']['user_total']}  cmd: {retDict['cmd_total']}"
                ), Module.Divider())
            log_img_src = await bot_upimg.client.create_asset("../screenshot/log.png")
            c.append(Module.Container(Element.Image(src=log_img_src)))
            c.append(
                Module.Section(
                    Struct.Paragraph(2, Element.Text(f"{res_text['name'][:5000]}", Types.Text.KMD),
                                     Element.Text(f"{res_text['user'][:5000]}", Types.Text.KMD))))  #限制字数才能发出来
            cm.append(c)
            await msg.reply(cm)
        else:
            await msg.reply(f"您没有权限执行此命令！")
    except:
        _log.exception("Exception occur")
        await msg.reply(f"ERR! [{GetTime()}] log_list\n```\n{traceback.format_exc()}\n```")


@bot.command(name='mem')
async def proc_check(msg: Message, *arg):
    BotLog.logMsg(msg)
    try:
        if msg.author_id == master_id:
            cm = await BotLog.get_proc_info()
            await msg.reply(cm)
    except:
        _log.exception("Exception occur")
        await msg.reply(f"ERR! [{GetTime()}] mem\n```\n{traceback.format_exc()}\n```")


#在阿狸开机的时候自动加载所有保存过的cookie
@bot.on_startup
async def loading_cache(bot: Bot):
    try:
        global debug_ch, cm_send_test
        cm_send_test = await bot_upimg.client.fetch_public_channel(config['channel']["img_upload_ch"])
        debug_ch = await bot.client.fetch_public_channel(config['channel']['debug_ch'])
        _log.info("[BOT.TASK] fetch_public_channel success")
    except:
        _log.error("[BOT.TASK] fetch_public_channel failed")
        _log.exception("Exception occur")
        os._exit(-1)  #出现错误直接退出程序

    _log.info("[BOT.TASK] loading cookie start")
    global UserAuthDict
    log_str_success = "[BOT.TASK] load cookie success  = Au:"
    log_str_failed = "[BOT.TASK] load cookie failed!  = Au:"
    log_not_exits = "[BOT.TASK] cookie path not exists = Au:"
    # 遍历用户列表
    for user, uinfo in VipUserDict.items():
        cookie_path = f"./log/cookie/{user}.cke"
        #如果路径存在，那么说明已经保存了这个vip用户的cookie
        if os.path.exists(cookie_path):
            auth = EzAuth()
            auth.load_cookies(cookie_path)  #加载cookie
            ret_bool = await auth.reauthorize(exp_print=False)  #尝试登录
            if ret_bool:  # True登陆成功
                UserAuthDict[user] = {"auth": auth, "2fa": False}  #将对象插入
                log_str_success += f"({user})"
            else:
                del auth  # 删除对象
                log_str_failed += f"({user}) "
                continue
        else:
            log_not_exits += f"({user}) "
            continue
    # 结束任务
    _log.info("TASK.INFO\n\t" + log_str_success + "\n\t" + log_str_failed + "\n\t" + log_not_exits)
    _log.info(f"[BOT.TASK] loading user cookie finished")

    # api缓存的用户列表
    log_str_success = "[BOT.TASK] api load cookie success  = Au:"
    log_str_failed = "[BOT.TASK] api load cookie failed!  = Au:"
    log_not_exits = "[BOT.TASK] api cookie path not exists = Au:"
    # 遍历api用户列表
    for user in ApiAuthLog:
        cookie_path = f"./log/cookie/api/{user}.cke"
        #如果路径存在，那么说明已经保存了这个vip用户的cookie
        if os.path.exists(cookie_path):
            auth = EzAuth()
            auth.load_cookies(cookie_path)  #加载cookie
            ret_bool = await auth.reauthorize(exp_print=False)  #尝试登录
            if ret_bool:  # True登陆成功
                UserAuthDict[user] = {"auth": auth, "2fa": False}  #将对象插入
                log_str_success += f"({user})"
            else:
                del auth  # 删除对象
                log_str_failed += f"({user}) "
                continue
        else:
            log_not_exits += f"({user}) "
            continue
    # 结束任务
    _log.info("TASK.INFO\n\t" + log_str_success + "\n\t" + log_str_failed + "\n\t" + log_not_exits)
    _log.info(f"[BOT.TASK] loading api user cookie finished")


# 开机 （如果是主文件就开机）
if __name__ == '__main__':
    # 开机的时候打印一次时间，记录开启时间
    _log.info(f"[BOT] Start at: [%s]" % start_time)
    bot.run()