import traceback
import io
from khl import Message, Bot
from PIL import Image
from ..ShopImg import img_requestor
from ..FileManage import ValBundleList
from .Val import fetch_skins_all, fetch_item_price_all, fetch_bundles_all, ValSkinList, ValPriceList
from ..log.Logging import _log

# 更新本地保存的皮肤
async def update_skins(msg: Message) -> bool:
    try:
        global ValSkinList
        skins = await fetch_skins_all()
        ValSkinList.value = skins
        # 写入文件
        ValSkinList.save()
        _log.info(f"update_skins finished!")
        return True
    except Exception as result:
        _log.exception("Exception occur")
        await msg.reply(f"ERR! update_skins\n```\n{traceback.format_exc()}\n```")
        return False


# 更新捆绑包
async def update_bundle_url(msg: Message, bot_upimg: Bot) -> bool:
    try:
        global ValBundleList
        resp = await fetch_bundles_all()  #从官方获取最新list
        if len(resp['data']) == len(ValBundleList):  #长度相同代表没有更新
            _log.info(f"len is the same, not need update")
            await msg.reply("BundleList_len相同，无需更新")
            return True

        for b in resp['data']:
            flag = 0
            for local_B in ValBundleList:  #不在
                if b['uuid'] == local_B['uuid']:  #相同代表存在无需更新
                    flag = 1  #找到了，无需更新
                    break

            if flag != 1:  #不存在,创建图片准备上传 (原有捆绑包图片如果每次都上传，会让bot很卡)
                bg_bundle_icon = Image.open(io.BytesIO(await img_requestor(b['displayIcon'])))
                imgByteArr = io.BytesIO()
                bg_bundle_icon.save(imgByteArr, format='PNG')
                imgByte = imgByteArr.getvalue()
                _log.info(f"Uploading | {b['displayName']}")
                bundle_img_src = await bot_upimg.client.create_asset(imgByte)
                _log.info(f"{b['displayName']} | url: {bundle_img_src}")
                b['displayIcon2'] = bundle_img_src  #修改url
                ValBundleList.append(b)  #插入

        ValBundleList.save()
        _log.info(f"update_bundle_url finished!")
        return True
    except Exception as result:
        _log.exception("Exception occur")
        await msg.reply(f"ERR! update_bundle_url\n```\n{traceback.format_exc()}\n```")
        return False


# 因为下方获取物品价格的操作需要authtoken，自动更新容易遇到token失效的情况
async def update_price(msg: Message, userdict) -> bool:
    try:
        global ValPriceList
        # 调用api获取价格列表
        prices = await fetch_item_price_all(userdict)
        test = prices["Offers"] # 暴力判断是否有这个键值，没有则keyerr
        ValPriceList.value = prices  # 所有价格的列表
        # 写入文件
        ValPriceList.save()
        _log.info(f"update_item_price finished!")
        return True
    except Exception as result:
        _log.exception("Exception occur")
        await msg.reply(f"ERR! update_price\n```\n{traceback.format_exc()}\n```")
        return False