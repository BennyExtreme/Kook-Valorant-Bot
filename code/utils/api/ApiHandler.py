import json
import time
import threading
import traceback

from utils.valorant.EzAuth import EzAuthExp,EzAuth
from utils.api.ApiToken import check_token_rate
from utils.Gtime import GetTime
from utils.KookApi import kook_create_asset
from utils.valorant.Val import fetch_daily_shop, fetch_vp_rp_dict
from utils import ShopRate,ShopImg

# bot的配置文件
from utils.FileManage import config,ApiAuthCache,ApiAuthLog,_log
# 用来给kook上传文件的bot token
api_bot_token = config['token']['api_bot_token']
# 默认的背景图
img_bak_169 = 'https://img.kookapp.cn/assets/2022-10/KcN5YoR5hC0zk0k0.jpg'
img_bak_11 = 'https://img.kookapp.cn/assets/2023-01/lzRKEApuEP0rs0rs.jpg'


# # 上传到lsky (这个上传很麻烦，lsky只认open打开的图片)
# gLock = asyncio.Lock() # 创建一把锁，用于保存文件
# async def lsky_upload(bg):
#     await gLock.acquire()# 上锁
#     path = "./log/api_img_temp.png"
#     bg.save(path, format='PNG')
#     img = open(path,'rb')
#     gLock.release()     # 释放锁
#     # lsky的连接和token写入配置文件，方便修改
#     url = f"{config['lsky']['url']}/api/v1/upload"
#     header = {
#         "Authorization": f"Bearer {config['lsky']['token']}",
#         "Accept": "application/json"
#     }
#     params = {'strategy_id':3}
#     myfiles = {'file': img}
#     ret = requests.post(url, headers=header, params=params,files=myfiles)  # 请求api
#     ret = ret.json()
#     _log.debug(ret)
#     if ret['status']: # 上传成功
#         return {'code':0,'data':ret['data']['links'],'message':ret['message']}
#     # 上传失败
#     return {'code':200,'data':ret['data'],'message':ret['message']}


# 基本画图操作
async def base_img_request(params, list_shop, vp1=0, rp1=0):
    # 自定义背景
    if 'img_src' in params and 'http' in params['img_src']:
        img_src = params['img_src']
    else:
        img_src = img_bak_169  # 默认背景16-9
        if 'img_ratio' in params and params['img_ratio'] == '1':
            img_src = img_bak_11  # 默认背景1-1

    # 开始画图
    ret = { "status": False,"value":"no need to img draw"} # 初始化ret为不需要画图
    cacheRet = {"status":False,"img_url":"err" } # 是否需要上传图片(false代表需要)
    start = time.perf_counter()
    if 'img_ratio' in params and params['img_ratio'] == '1':
        # 是1-1的图片，检测有没有使用自定义背景图
        if img_src == img_bak_11: # 没有自定义背景图
            # 检测是否有缓存命中
            cacheRet = await ShopRate.query_ShopCache(list_shop)
        # 缓存命中失败(需要画图)
        if not cacheRet['status']:
            ret = await ShopImg.get_shop_img_11(list_shop, bg_img_src=img_src)
    else:  # 只有16-9的图片需获取vp和r点
        ret = await ShopImg.get_shop_img_169(list_shop, vp=vp1, rp=rp1, bg_img_src=img_src)
    # 打印计时
    _log.info(f"Api imgDraw | {format(time.perf_counter() - start, '.3f')}")  # 结果为浮点数，保留两位小数

    # 开始上传图片
    start = time.perf_counter() # 更新start计时器
    # 判断缓存是否命中
    if cacheRet['status']: # 命中了
        dailyshop_img_src = cacheRet['img_url']
        _log.info(f"Api imgUrl(cache) | {dailyshop_img_src}")
        return {'code': 0, 'message': dailyshop_img_src, 'info': '商店图片获取成功，缓存命中'}
    # 缓存没有命中，但是获取画图结果成功
    if ret['status']:
        bg = ret['value'] # 这个值是pil的结果
        img_src_ret = await kook_create_asset(api_bot_token, bg)  # 上传图片到kook
        # img_src_ret = await lsky_upload(bg) # 上传图片到lsky
        if img_src_ret['code'] == 0: # 上传图片成功
            _log.info(f"Api | kook_create_asset success | {format(time.perf_counter() - start, '.3f')}")
            dailyshop_img_src = img_src_ret['data']['url']
            # 初始值是err，调用了query_ShopCache失败，返回值更新为空
            if cacheRet['img_url'] != 'err':
                await ShopRate.update_ShopCache(skinlist=list_shop,img_url=dailyshop_img_src)
            _log.info(f"Api imgUrl | {dailyshop_img_src}")
            return {'code': 0, 'message': dailyshop_img_src, 'info': '商店图片获取成功'}
        else: # 上传图片失败
            _log.info(f"Api | kook_create_asset failed")
            return {'code': 200, 'message': 'img upload err', 'info': '图片上传错误'}
    else: # 出现图片违规或者背景图url无法获取
        err_str = ret['value']
        _log.error(err_str)
        return {'code': 200, 'message': 'img src err', 'info': '自定义图片获取失败'}


# 画图接口(仅画图)
async def img_draw_request(request):
    params = request.rel_url.query
    if "list_shop" not in params or 'token' not in params:
        _log.error(f"params needed: token/list_shop")
        return {
            'code': 400,
            'message': 'params needed: token/list_shop',
            'info': '缺少参数！示例: /shop-draw?token=api凭证&list_shop=四个皮肤uuid的list&vp=vp（可选）&rp=rp（可选）&img_src=自定义背景图（可选）',
            'docs': 'https://github.com/Aewait/Kook-Valorant-Bot/blob/main/docs/valorant-shop-img-api.md'
        }
    
    # params是multidict，传入的list_shop被拆分成了多个键值，需要合并
    list_shop = list()
    for key,value in params.items():
        if key == 'list_shop':
            list_shop.append(value)
    # 判断传入的皮肤数量是不是4个
    if len(list_shop) != 4:
        return {'code':200,'message':'list_shop len err! should be 4','info':'list_shop长度错误，皮肤数量不为4'}
    
    token = params['token']
    _log.debug(f"list_shop | {list_shop}")
    ck_ret = await check_token_rate(token)
    if not ck_ret['status']:
        return {'code': 200, 'message': ck_ret['message'], 'info': ck_ret['info']}
    # vp和rp必须同时给予，只给一个不算
    if 'vp' not in params or 'rp' not in params:
        return await base_img_request(params, list_shop)
    else:
        return await base_img_request(params, list_shop, int(params['vp']), int(params['rp']))

# 获取商店的请求
async def shop_get_request(params,account:str):
    # 1.参数检测
    isRaw = ('raw' in params and str(params['raw']) != '0') # 用户需要原始uuid
    isimgRatio = ( 'img_ratio' not in params or str(params['img_ratio']) != '1') # 判断是否有指定图片比例
    # 2.获取缓存中的auth对象
    if account not in ApiAuthCache['data']:
        return { "code":200,"message":"account不在ApiAuthCache缓存中，请先调用/login接口",
                "info":"account not in ApiAuthCache['data']" }
    # 2.1 判断通过，获取auth
    auth = ApiAuthCache['data'][account]['auth']
    assert isinstance(auth,EzAuth)
    # 2.2 重新登录
    ret = await auth.reauthorize()
    if not ret:
        return { "code":200,"message":"缓存信息失效，需要重新登录",
                "info":"cache reauthorize failed，please /login" }
    # 3 获取每日商店
    riotUser = auth.get_riotuser_token()
    resp = await fetch_daily_shop(riotUser)  
    _log.info(f'Api | fetch_daily_shop success')
    list_shop = resp["SkinsPanelLayout"]["SingleItemOffers"]  # 商店刷出来的4把枪
    res_vprp = {'vp': 0, 'rp': 0}  # 先初始化为0
    if isimgRatio or isRaw:
        res_vprp = await fetch_vp_rp_dict(riotUser)  # 只有16-9的图片需获取vp和r点
    # 如果用户需要raw，则返回皮肤uuid和vp rp的dict
    if isRaw:
        return { "code":0,"message":"获取原始接口返回值成功","info":"get raw response success","storefront":resp,"wallet":res_vprp}
    else:
        return await base_img_request(params, list_shop, res_vprp['vp'], res_vprp['rp'])

# 登录+画图
async def login_request(request,method = "GET"):
    params = request.rel_url.query
    if method=="POST":
        body = await request.content.read()
        params = json.loads(body.decode('UTF8'))
    # 判断必须要的参数是否齐全
    if 'account' not in params or 'passwd' not in params or 'token' not in params:
        _log.error(f"params needed: token/account/passwd")
        return {
            'code': 400,
            'message': 'params needed: token/account/passwd',
            'info': '缺少参数！示例: /shop-img?token=api凭证&account=Riot账户&passwd=Riot密码&img_src=自定义背景图（可选）',
            'docs': 'https://github.com/Aewait/Kook-Valorant-Bot/blob/main/docs/valorant-shop-img-api.md'
        }

    account = params['account']
    passwd = params['passwd']
    token = params['token']
    # 检测token速率，避免撞墙
    ck_ret = await check_token_rate(token)
    if not ck_ret['status']:
        return {'code': 200, 'message': ck_ret['message'], 'info': ck_ret['info']}

    try:
        # 登录，获取用户的token
        auth = EzAuth()
        resw = await auth.authorize(account,passwd)
        ApiAuthCache['data'][account] = {"auth": auth, "2fa": auth.is2fa } # 将对象插入
        # 没有成功，是2fa用户，需要执行/tfa
        if not resw['status']:
            return {'code': 0, 'message': "need provide email verify code", 'info': '2fa用户，请使用/tfa接口提供邮箱验证码'}
        
    except EzAuthExp.RatelimitError as result:
        _log.exception(f"Api login | RatelimitError")
        return {'code': 200, 'message': "EzAuthExp.RiotRatelimitError", 'info': 'riot登录api超速，请稍后重试'}

    # 走到这里，代表不是2fa用户，且登陆成功
    _log.info(f"Api login | user auth success")
    # 如果是GET方法，直接调用获取商店的操作
    if method == "GET": # /shop-img 接口是get的
        return await shop_get_request(params,account)
    # 保存cookie到本地
    if account not in ApiAuthLog:
        ApiAuthLog.append(account) # 记录已缓存的用户账户（方便开机加载）
    auth.save_cookies(f"./log/cookie/api/{account}.cke") 
    return {'code': 0, 'message': "auth success", 'info': '登录成功！'}


# 邮箱验证的post
async def tfa_code_requeset(request):
    body = await request.content.read()
    params = json.loads(body.decode('UTF8'))
    if 'account' not in params or 'vcode' not in params or 'token' not in params:
        _log.error(f"params needed: token/account/vcode")
        return {
            'code': 400,
            'message': 'params needed: token/account/vcode',
            'info': '缺少参数！示例: /tfa?token=api凭证&account=Riot账户&vcode=邮箱验证码',
            'docs': 'https://github.com/Aewait/Kook-Valorant-Bot/blob/main/docs/valorant-shop-img-api.md'
        }

    account = params['account']
    vcode = params['vcode']
    token = params['token']

    global ApiAuthCache
    if account not in ApiAuthCache['data']:
        return { 'code': 200,'message': 'Riot account not in ApiAuthCache',
            'info': '拳头账户不在dict中，请先请求/shop-img或/login接口' }
    try:
        auth = ApiAuthCache['data'][account]['auth']
        assert isinstance(auth,EzAuth)
        res = await auth.email_verfiy(vcode)
    except EzAuthExp.MultifactorError as result:
        _log.exception("Api tfa | MultifactorError")
        if "multifactor_attempt_failed" in str(result):
            return { 'code': 200,'message': 'multifactor_attempt_failed',
                     'info': '两步验证码错误，请在10min内重新调用此接口重传','vcode': vcode }
        # 其他情况
        return {'code': 200,'message': '2fa auth_failure','info': '两步验证登陆错误，请重新操作','vcode': vcode}
    # 走到这里，代表是2fa用户，且登陆成功
    _log.info("Api tfa | 2fa user auth success")
    # 保存cookie到本地
    if account not in ApiAuthLog:
        ApiAuthLog.append(account) # 记录已缓存的用户账户（方便开机加载）
    auth.save_cookies(f"./log/cookie/api/{account}.cke") 
    return  {'code': 0, 'message': "2fa auth success", 'info': '2fa用户登录成功！'}


# 更新leancloud
from utils.ShopRate import update_ShopCmp
async def shop_cmp_request(request):
    body = await request.content.read()
    params = json.loads(body.decode('UTF8'))
    if 'best' not in params or 'worse' not in params or 'token' not in params or 'platform' not in params:
        _log.error("params needed: token/best/worse/platform")
        return {
            'code': 400,
            'message': 'params needed: token/best/worse/platform',
            'info': '缺少参数！请参考api文档，正确设置您的参数',
            'docs': 'https://github.com/Aewait/Kook-Valorant-Bot/blob/main/docs/valorant-shop-img-api.md'
        }
    
    best = params['best']
    worse = params['worse']
    platform = params['platform']
    # 调用已有函数更新，保证线程安全
    upd_ret = await update_ShopCmp(best=best,worse=worse,platform=platform)
    ret = {'code':0,'message':upd_ret['status'],'info':'ShopCmp更新成功'}
    # 如果正常，那就是0，否则是200
    if not upd_ret['status']:
        ret['code'] = 200
        ret['info'] = 'ShopCmp更新错误'

    return ret


from utils.FileManage import AfdWebhook
from khl.card import CardMessage, Card, Module, Types, Element


# 爱发电webhook
async def afd_request(request, bot):
    body = await request.content.read()
    params = json.loads(body.decode('UTF8'))
    global AfdWebhook
    AfdWebhook.append(params)

    text = ""
    if 'plan_title' in params['data']['order']:
        text = f"商品 {params['data']['order']['plan_title']}\n"
    user_id = params['data']['order']['user_id']
    user_id = user_id[0:6]
    text += f"用户 {user_id}\n"
    for i in params['data']['order']['sku_detail']:
        text += f"发电了{i['count']}个 {i['name']}\n"
    text += f"共计 {params['data']['order']['total_amount']} 猿"

    trno = params['data']['order']['out_trade_no']
    trno_f = trno[0:8]
    trno_b = trno[-4:]
    trno_f += "####"
    trno_f += trno_b

    cm = CardMessage()
    c = Card(Module.Header(f"爱发电有新动态啦！"), Module.Context(Element.Text(f"订单号: {trno_f}")), Module.Divider(),
             Module.Section(Element.Text(text, Types.Text.KMD)))
    cm.append(c)
    _log.debug(json.dumps(cm))
    debug_ch = await bot.client.fetch_public_channel(config['channel']['debug_ch'])
    await bot.client.send(debug_ch, cm)
    _log.info(f"trno:{params['data']['order']['out_trade_no']} | afd-cm-send")
    return {"ec": 200, "em": "success"}
