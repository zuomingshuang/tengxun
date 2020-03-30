from gevent import monkey
monkey.patch_all()
import gevent
from gevent import pool
import requests
import re
import json
import pandas as pd
import xlsxwriter


#获取每一集的id
def get_vid_list():
    url='https://v.qq.com/x/cover/rjae621myqca41h/i0032qxbi2v.html?ptag=360kan.tv.free'
    res=requests.get(url=url,headers=Headers)
    html=res.text
    # print(html)
    vid_list=re.findall(r'"V":"([0-9a-z]{11})","E":(\d{1,2})',html)
    # print(vid_list)
    return vid_list

#获取每一页弹幕数据
def get_per_danmu_html(target_id,timestamp):
    url='https://mfm.video.qq.com/danmu'
    data={
        'otype':'json',
        'callback':'jQuery19104794869679050451_1577190443637',
        # 'target_id':'4456608340&vid=c0032ai1iwq',
        'target_id':target_id ,
        'session_key':'700065,42782,1577190440',
        'timestamp':timestamp,
        '_':'1577190443660'
    }
    res=requests.get(url=url,params=data,headers=Headers)
    html=res.text
    # print(html)
    return html

#获取每一集的target_id
def get_target_id(v_id):
    base_url = 'https://access.video.qq.com/danmu_manage/regist?vappid=97767206&vsecret=c0bdcbae120669fff425d0ef853674614aa659c605a613a4&raw=1'
    pay = {"wRegistType":2,"vecIdList":[v_id],
       "wSpeSource":0,"bIsGetUserCfg":1,
       "mapExtData":{v_id:{"strCid":"wu1e7mrffzvibjy","strLid":""}}}
    html = requests.post(base_url,json = pay,headers = Headers)
    bs = json.loads(html.text)
    danmu_key = bs['data']['stMap'][v_id]['strDanMuKey']
    target_id = danmu_key[danmu_key.find('targetid') + 9 : danmu_key.find('vid') - 1]
    return target_id

#获取弹幕html数据
def get_danmu_html(html_list,vid,E):
    try:
        tar_id = get_target_id(vid)
        target_id = '{tar_id}&vid={vid}'.format(tar_id=tar_id, vid=vid)
        timestamp = 0
        # print(target_id)
        while True:
            html = get_per_danmu_html(target_id=target_id, timestamp=timestamp)
            if '"comments":[]' in html:
                break
            html_list.append((E, html))
            timestamp += 30
            print('成功爬取第%s集的第%s页的弹幕' % (E, str(timestamp)))
    except Exception as e:
        print(e)


#获取弹幕html数据列表
def danmu_html_list():
    html_list=[]
    tasks=[]
    pl=pool.Pool(20)
    for vid,E in get_vid_list():
        p=pl.spawn(get_danmu_html,html_list,vid,E)
        tasks.append(p)
    gevent.joinall(tasks)
    return html_list


#解析所有HTML并保存数据
def save_danmu_data():
    data_dict = {'集数':[],'用户昵称': [], '用户vip等级': [], '时间点(秒)': [], '点赞数量': [], '弹幕内容': []}
    html_list=danmu_html_list()
    for E,html in html_list:
        try:
            # print(E,html)
            html=re.sub(r'^jQuery.*?\(','',html).strip(r'\)')
            html=json.loads(html,strict=False)
            comments=html['comments']
            # print(comments)
        except Exception as e:
            print(e)
        for comment in comments:
            try:
                content=comment['content']  #弹幕内容
                upcount = comment['upcount']  # 点赞数量
                timepoint = comment['timepoint']  # 时间点
                opername = comment['opername']  # 用户昵称
                uservip_degree = comment['uservip_degree']  # 用户vip等级

                print(opername+':'+content)
                data_dict['集数'].append('第%s集'%E)
                data_dict['用户昵称'].append(opername)
                data_dict['用户vip等级'].append(uservip_degree)
                data_dict['时间点(秒)'].append(timepoint)
                data_dict['点赞数量'].append(upcount)
                data_dict['弹幕内容'].append(content)
            except Exception as e:
                print(e)
    print('正在保存弹幕数据...')
    df=pd.DataFrame(data_dict).drop_duplicates(['用户昵称','用户vip等级','时间点(秒)','点赞数量','弹幕内容'])
    df.to_excel('庆余年弹幕.xlsx',index=False,engine='xlsxwriter')

#利用弹幕内容生成词云
def my_word_cloud():
    from wordcloud import WordCloud
    import PIL.Image as img
    import jieba
    import numpy
    df=pd.read_excel('庆余年弹幕.xlsx')
    # print(list(df['弹幕内容'].values))
    # exit()
    mystr=str(list(df['弹幕内容'].values)).strip()
    mystr=re.sub(r'哈|\s','',mystr)
    words=jieba.cut(mystr)
    text=' '.join(words)
    mask=numpy.array(img.open('man.png'))
    word_cloud=WordCloud(
        background_color='white',
        width=400,
        height=400,
        max_words=200,
        max_font_size=50,
        mask=mask,
        font_path='FZLTXIHK.TTF',
        stopwords={'xa0':0,'因为':0,'这个':0,'这么':0,'所以':0,'原来':0}
    ).generate(text)
    WordCloud.to_image(word_cloud).save('庆余年弹幕.png')

if __name__=='__main__':
    Headers={'user-agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'}

    # #爬取并保存弹幕数据
    # save_danmu_data()

    #利用弹幕内容生成词云
    my_word_cloud()