#!/usr/bin/env python
# -*- coding:gb18030 -*-
#  FileName    : SadFarmer.py 
#  Author      : WangMaoMao
#  Created     : Tue Aug 25 19:15:47 2009 by Feather.et.ELF 
#  Description : У��(����)����ũ���������� ����ũ�� 0.1.6
#  Time-stamp: <2009-08-27 00:46:42 andelf> 



import socket
socket.setdefaulttimeout(10.0)
import urllib
import urllib2
import time
import simplejson
import md5
import logging
import re
import os
from sys import exit
from collections import defaultdict
try:
    import cPickle as Pickle
except:
    import Pickle

__VERSION__ = '0.1.6'

defaultConfig = {"help-friends" : True,
                 "steal" : True,
                 "full-simulate" : False,
                 "cache-file" : "./farmer.cache",
                 "sell-all" : False
                 }

class HappyFarm(object):
    def __init__(self, email=None, password=None, autoInit=True, config=defaultConfig):
        self.email = email
        self.config = config
        self.inited = False
        self._timeDelta = 0
        self._timeStamp = 0
        self._stateChanged = False        # ��־����
        self.userList = []
        self.userDict = {}
        self._profit = {'direction': u"�ϼ�:", 'harvest':0, 'money':0, 'exp':0, 'charm':0,
                        'crops' : defaultdict(int) }
        self.jsonDecode = simplejson.JSONDecoder(encoding='gb18030').decode
        cookie_handler = urllib2.HTTPCookieProcessor()
        self.opener = urllib2.build_opener(cookie_handler)
        self.opener.addheaders = [('User-agent', 'Mozilla/5.0 SadFarmer/0.1 By WangMaoMao'),
                                  ('Referer', 'http://xn.cache.fminutes.com/images/v3/module/Main.swf?v=4'),
                                  ('x-flash-version', '11,0,32,18')] # flash 11 better?
        if email and password:
            self.login(email, password)
        else:
            try:
                cookie = self.getCookieViaCOM()
            except :
                logging.error("�޷�ͨ�� COM ���ӻ���û���Ϣ!")
                os.system('pause')
                exit(-1)
            self.opener.addheaders += [ ('Cookie', cookie) ]
        if autoInit:
            self.initFarm()
    def initFarm(self):
        self._initMyInfo()
        self._initShopInfo()
        self.updateMyPackage()
        self.updateAllFarms()
        self._timeStamp = self.now()
        self.inited = True
    def _initMyInfo(self):
        res = self.request( self.buildUrl('user', 'run') )
        logging.info("��ʼ���Լ�ũ����Ϣ.")
        logging.info("�û�: %s ������ʱ��: %d ������: %d.",
                     res.get('user', {}).get('userName', 0).encode('gb18030'),
                     res.get('serverTime', {}).get('time', 0),
                     len(res.get('farmlandStatus', [])) )
        self._uid = res['user']['uId']
        self._farmlandStatus = res['farmlandStatus'] # or needless
        self._timeDelta = int(time.time() - res['serverTime']['time'])
        logging.info("ʱ��ͬ���ɹ�. ʱ��Ϊ %d.", self._timeDelta)
    def updateFarm(self, ownerId=0):
        res = self.request( self.buildUrl('user', 'run', 1),
                            {'ownerId': ownerId} )
        if ownerId== 0:
            self._farmlandsStatus[self._uid] = res['farmlandStatus']
            self._farmlandStatus = res['farmlandStatus']
            logging.info("�����Լ�ũ����Ϣ. ������: %d.", len(res['farmlandStatus']) )
        else:
            self._farmlandsStatus[ownerId] = res['farmlandStatus']
            logging.info("�����û� %s(id:%s) ũ����Ϣ. ������: %d.",
                         self.id2userName(ownerId),
                         str(ownerId), len(res['farmlandStatus']) )

    def updateMyPackage(self):
        res = self.request( self.buildUrl('Package', 'getPackageInfo') )
        logging.info("���±�����Ϣ ����1(����).")
        for i in res.get('1', []):  # May fail, so use get()
            logging.info("%s %d ��", i['cName'].encode('gb18030'), int(i['amount']) )
        self._packageInfo = res.get('1', [])
        
    def _readCache(self, key=None):
        if not self.config['cache-file']:
            return {}
        try:
            logging.info("���뻺���ļ� %s.", self.config['cache-file'])
            db = file(self.config['cache-file'], 'rb')
            data = Pickle.load(db)
            db.close()
            return data[key] if key else data
        except:
            return {}
    def _writeCache(self, data, isUserData=True):
        if not self.config['cache-file']:
            return
        try:
            logging.info("д�뻺���ļ� %s .", self.config['cache-file'])
            gData = self._readCache()
            if isUserData:
                gData[self.email] = dict(data, timeStamp=self._timeStamp)
            else:
                gData.update(data, timeStamp=self._timeStamp)
            db = file(self.config['cache-file'], 'wb')
            Pickle.dump(gData, db)
            db.close()
        except:
            logging.warning("�����ļ�д��ʧ��.")
    def saveToCache(self, user=True, env=True):
        if user:
            self._writeCache(dict(userList=self.userList, userDict=self.userDict))
        if env:
            self._writeCache(dict(shopInfo=self._shopInfo), isUserData=False)
    def _initShopInfo(self):
        data = self._readCache(key='shopInfo')
        if data:
            self._shopInfo = data
        else:
            res = self.request( self.buildUrl('shop', 'getShopInfo', type=[1]) )
            self._shopInfo = res.get('1', [])
            self.saveToCache(user=False, env=True)
        logging.info("��ʼ���̵���Ʒ ����1(����).")
        logging.info("�õ� %d ��������Ϣ.", len(self._shopInfo))
        
    def _initUserInfo(self):
        data = self._readCache(key=self.email)
        if data:
            try:
                assert data['userList']>= 1
                self.userList = data['userList']
                self.userDict = data['userDict']
                logging.info("���سɹ�. ��� %d �û�.", len(self.userList))
                return
            except:
                pass
        logging.warning("�����ȡʧ��. ���������ȡ.")
        res = self.request( self.buildUrl('friend'),
                            {'fv': 0,
                             'refresh': 'true'} )
        res = res['data'] if 'data' in res else res
        # res = res['data'] # fuck ? server modified?
        self.userList = [int(f['userId']) for f in res if int(f['exp'])!= 0] # note: last is mine
        self.userDict = dict([(int(f['userId']), f) for f in res if int(f['exp'])!= 0])
        logging.info("��� %d �û�.", len(self.userList))
        self.saveToCache(user=True, env=False)
    def updateAllFarms(self):
        self._farmlandsStatus = {}  # rebuild
        if not self.userList:
            self._initUserInfo()
        for uid in self.userList:
            self.updateFarm(uid)
        logging.info("��� %d ���û�ũ����Ϣ.", len(self.userList))
        self._farmlandStatus = self._farmlandsStatus[self._uid]
    def sell(self, all=True, cId=0, number=1):
        ownerId = self._uid
        if not self.config['sell-all']:
            return
        if all:
            logging.info("���۲ֿ����й�ʵ. (������)")
            res = self.request( self.buildUrl('repertory', 'saleAll'), {'type':1})
        else:
            res = self.request( self.buildUrl('repertory', 'sale'),
                                {'cId':cId,
                                 'number' : number} )
        self.log(res)

    def harvest(self, autoRefresh=True):
        ownerId = self._uid
        # harvest my only
        for i, land in enumerate(self._farmlandStatus):
            if land['b'] == 6: # ����
                self._stateChanged = True
                logging.info("����%d %s ����. �ջ�!", i, self.id2cName(land['a']))
                res = self.request( self.buildUrl('farmlandstatus', 'harvest'),
                                    {'ownerId': ownerId,
                                     'place'  : i } )
                self.log(res)
        if self._stateChanged and autoRefresh:
            self.updateFarm()
        self._stateChanged = False
    def buy(self, howMany=1, id=None, type=1):
        if not id:
            logging.warning("������èèϲ��õ��, ������Ҳ������õ��!")
            id = 101
            type = 1
        logging.info("���� %s(����%d) %d ��",
                     self.id2cName(id), type, howMany)
        res = self.request( self.buildUrl('shop', 'buy'),
                            {'id' : id,
                             'type' : type,
                             'number' : howMany } )
        self.log(res)
        
    def scarify(self, ownerId=None, autoRefresh=True):  # ����
        ownerId = ownerId if ownerId else self._uid
        # scarify my only
        for i, land in enumerate(self._farmlandStatus):
            if land['b'] == 7: # �ݸ�״̬
                self._stateChanged = True
                logging.info("����%d %s ��ή. ����!", i, self.id2cName(land['a']))
                res = self.request( self.buildUrl('farmlandstatus', 'scarify'),
                                    {'ownerId': ownerId,
                                     'place'  : i } )
                self.log(res)
        if self._stateChanged and autoRefresh:
            self.updateFarm()
        self._stateChanged = False

    def planting(self, ownerId=None, autoRefresh=True):
        ownerId = ownerId if ownerId else self._uid
        emptyLands = [i for i,land in enumerate(self._farmlandStatus) if land['b']==0]
        seedNeeded = len(emptyLands)
        if seedNeeded<= 0:
            logging.info("����Ҫ��ֲ������.")
            return 
        logging.info("���ֿյ� %d ��.", seedNeeded)
        cItems = sorted(self._packageInfo, key = lambda d:d['cId'])[::-1]
        seedHaveGot = sum(seed['amount'] for seed in cItems)
        if seedNeeded> seedHaveGot:
            logging.warning("���Ӳ���, �Զ�����.")
            self.buy(seedNeeded - seedHaveGot)
            self.updateMyPackage()
            return self.planting(ownerId)
        for i in emptyLands:
            for cItem in cItems:
                if cItem['amount']<= 0:
                    continue
                logging.info("����%d ��ֲ %s.", i, self.id2cName(cItem['cId']))
                res = self.request( self.buildUrl('farmlandstatus', 'planting'),
                                    {'ownerId' : ownerId,
                                     'cId' : cItem['cId'],
                                     'place' : i } )
                self.log(res)
                break
        self.updateMyPackage()
        if autoRefresh:
            self.updateFarm() # default to mine
        
    def doMisc(self, ownerId=None, autoRefresh=True):
        ownerId = ownerId if ownerId else self._uid
        for i, land in enumerate( self._farmlandsStatus[ownerId] ):
            if land['h'] == 0: # �ɺ�
                self._stateChanged = True
                logging.info("�û� %s(id:%d) ����%d %s �ɺ�. ������ˮ!", self.id2userName(ownerId),
                             ownerId, i, self.id2cName(land['a']))
                res = self.request( self.buildUrl('farmlandstatus', 'water'),
                                    {'ownerId': ownerId,
                                     'place'  : i } )
                self.log(res)
            if land['t'] != 0: # ���Ѫ��
                land['g']+= 1
            for _ in xrange( land['g'] ): # ������
                self._stateChanged = True
                logging.info("�û� %s(id:%d) ����%d %s ����. ����ɱ��!", self.id2userName(ownerId),
                             ownerId, i, self.id2cName(land['a']))
                res = self.request( self.buildUrl('farmlandstatus', 'spraying'),
                                    {'tId' : 0,
                                     'ownerId': ownerId,
                                     'place'  : i } )
                self.log(res)
            for _ in xrange( land['f'] ): # ����, FIXME: ���ܲ���
                self._stateChanged = True
                logging.info("�û� %s(id:%d) ����%d %s ����. ��������!", self.id2userName(ownerId),
                             ownerId, i, self.id2cName(land['a']))
                res = self.request( self.buildUrl('farmlandstatus', 'clearWeed'),
                                    {'tId' : 0,
                                     'ownerId': ownerId,
                                     'place'  : i } )
                self.log(res)
        if self._stateChanged and autoRefresh:
            self.updateFarm(ownerId)
        self._stateChanged = False
            
    def scrounge(self, ownerId, autoRefresh=True): # ͵��
        if ownerId == self._uid or ownerId == 235795214:
            return # ��͵�Լ���
        for i, land in enumerate( self._farmlandsStatus[ownerId] ):
            if land['b'] == 6 and land['m'] > land['l'] and land['n']>=2:
                self._stateChanged = True
                logging.info("�û� %s(id:%d) ����%d[%s] ��͵��.", self.id2userName(ownerId),
                             ownerId, i, self.id2cName(land['a']))
                res = self.request( self.buildUrl('farmlandstatus', 'scrounge'),
                                    {'ownerId': ownerId,
                                     'place'  : i } )
                self.log(res)
        if self._stateChanged and autoRefresh:
            self.updateFarm(ownerId)
        self._stateChanged = False

    def runSimple(self):
        if not self.inited:
            self.initFarm()
        self.harvest()
        self.scarify()
        self.planting()
        self.doMisc()
        # self._doMisc()
        for i in self.userList:
            if self.config['help-friends']:
                self.doMisc(i, autoRefresh=False) # �������º�͵�� 
            if self.config['steal']:
                self.scrounge(i)
        self._timeStamp = self.now()
        if self.config['sell-all']:
            self.sell()

        # adds more here
    def refresh(self):
        self.updateAllFarms()
        self.updateMyPackage()
        self._timeStamp = self.now()
    
    def log(self, res, additionalInfo = '.'):
        message = []
        if 'direction' in res:
            message.append(res['direction'].encode('gb18030'))
        if 'harvest' in res:
            message.append("�ջ� %s" % str(res['harvest']) )
            self._profit['harvest'] += int(res['harvest'])
            if 'status' in res:
                self._profit['crops'][int(res['status']['cId'])] += int(res['harvest'])
                message.append("���� %s" % self.id2cName(res['status']['cId']))
        if 'cName' in res:
            message.append(res['cName'].encode('gb18030'))
        if 'num' in res:
            message.append("%s ��" % str(res['num']))
        if 'money' in res:
            message.append("��Ǯ %s" % str(res['money']))
            self._profit['money'] += int(res['money'])
        if 'exp' in res:
            message.append("���� %s" % str(res['exp']) )
            self._profit['exp'] += int(res['exp'])
        if 'charm' in res:
            message.append("���� %s" % str(res['charm']) )
            self._profit['charm'] += int(res['charm'])
        message.append(additionalInfo)
        logging.info( (' '.join(message)).strip())
    def logProfit(self):
        message = ["��������, ����˴��ջ�...\n==================== �ջ��嵥 ======================\n",]
        j = 0
        moneySum = 0
        for i,v in self._profit['crops'].items():
            if v == 0:
                continue
            message.append('%-14s %-4d %-5d' % (self.id2cName(i), v, self.id2money(i, v)))
            moneySum+= self.id2money(i,v)
            j+= 1
            message.append('\n' if j%2== 0 else ' | ')
        message.append("\n���������ۺϽ�Ǯ %d." % moneySum)
        logging.info(''.join(message))
        self.log(self._profit)
        self._profit = {'direction': u"�ϼ�:", 'harvest':0, 'money':0, 'exp':0, 'charm':0,
                        'crops' : defaultdict(int) } # re_init
    def id2cName(self, cid): # corn name
        cid = int(cid)
        try:
            return [c['cName'].split()[0] for c in self._shopInfo if c['cId']==cid][0].encode('gb18030')
        except:
            return "cID#%d" % cid
    def id2money(self, cid, num=1):
        cid = int(cid)
        try:
            return [int(c['sale'])*num for c in self._shopInfo if c['cId']==cid][0]
        except:
            return 0
    def id2userName(self, uid):
        return self.userDict.get(int(uid), {}).get('userName', u'��').encode('gb18030')

    def id2level(self, uid=None):
        uid = int(uid) if uid else self._uid
        exp = self.userDict[uid]['exp']
        for i in xrange(100):
            if i*(i+1)>= exp:
                return i-1

    def login(self, email, password):
        logging.info("ģ��ҳ���½... �û�: %s.", email)
        url = "http://login.renren.com/Login.do"
        data = {'email' : email,
                'password' :  password,
                'origURL' : "http://apps.renren.com/happyfarm" }
        res = self.request(url, data, jsonFormat=False)
        url = re.findall(r'<iframe name="iframe_canvas" src="([^"]+)"', res)
        if not url:
            logging.error("�û���/�������!")
            os.system('pause')
            exit(-1)
        url = url[0]
        url = url.replace('amp;', '').replace('?', '/?')
        logging.debug(url)
        # req.add_header("Referer", "http://apps.renren.com/happyfarm?origin=104")        
        self.request(url, jsonFormat=False)
        
    def getCookieViaCOM(self, visible = False):
        # win32 only, needs `save password` option on
        logging.info("ʹ�� COM ��ñ����û���½��Ϣ...")
        logging.warning("��ȷ�� IE ������Ϊ�Զ���½!")
        import win32com.client
        bro = win32com.client.Dispatch("InternetExplorer.Application")
        # show window
        bro.Visible = visible # toggle debug on or off
        bro.Navigate("http://apps.renren.com/happyfarm")    
        while bro.Busy:
            pass
        bro.Navigate("http://xn.hf.fminutes.com/api.php?mod=user&act=run&farmKey=97360611586906f6c79f11a02f66a72e&farmTime=1251042130&inuId=")
        while bro.Busy:
            pass # TODO: Add time out here
        while 'xn_sig_session_key' not in bro.Document.cookie:
            pass
        cookie = str(bro.Document.cookie)
        bro.Quit()
        return cookie
    
    def request(self, url, data = {}, jsonFormat=True):
        dataEncoded = urllib.urlencode(data)
        if data:
            req = urllib2.Request(url, data = dataEncoded)
        else:
            req = urllib2.Request(url)
        try:
            res = self.opener.open(req).read()
        except urllib2.URLError, err:
            logging.warning("��ȡ URL ��������: %s.", err)
            logging.warning("����......")
            return self.request(url, data, jsonFormat)
        except KeyboardInterrupt:
            logging.error("�û����!")
            exit(-1)
        except socket.error, err:
            logging.warning("socket ��������: %s.", err)
            logging.warning("����......")
            return self.request(url, data, jsonFormat)
        if jsonFormat:
            return self.jsonDecode(  res )
        else:
            return res
    
    def buildUrl(self, mod, act=None, flag=None, type=[], farmTime=None):
        result_url = ["http://xn.hf.fminutes.com/api.php?mod=" + mod]
        if act:
            result_url.append("act=" + act)
        if flag:
            result_url.append("flag=" + str(flag))
        if type:
            result_url.append("type=" + ','.join(map(str, type)))
        if not farmTime:                    # serverTime
            farmTime = str(self.now())
        farmKey = md5.new(farmTime + "15L3H4KH".lower()).hexdigest() # Magic~
        # wahaha~magic erlang:integer_to_list(16#ff2e301a, 23).
        result_url.append("farmKey=" + farmKey)
        result_url.append("farmTime=" + farmTime)
        result_url.append("inuId=")
        return '&'.join(result_url)
    
    def now(self):
        return int(time.time() - self._timeDelta)


__doc__ = ('='*80 + \
"""                ����ũ�� %s for renren.com
                    By ��èè(andelf@gmail.com)
                    Wed Aug 26 19:03:43 2009
                 #ʹ�ñ�������������κκ��, ���˲�����#
                      �벻ҪƵ��ִ��, ��ֹ�����!
                  ʹ�÷���:
                       1> ֱ������
                       2> �쿴���� --help
""" + '='*80) % (__VERSION__, )



if __name__ == '__main__':
    print __doc__
    from optparse import OptionParser
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage, version="%prog " + __VERSION__)
    parser.add_option("-f", "--log", "--log-file", default="./sadfarmer.log",
                      action="store", type="string", dest="logfile", metavar="FILENAME",
                      help=u"��¼��־�ļ���")
    parser.add_option("-c", "--cache", "--cache-file", default="./farmer.cache",
                      action="store", type="string", dest="cacheFile", metavar="FILENAME",
                      help=u"�����ļ���")
    parser.add_option("-u", "--user", "--username", "--email",
                      action="store", type="string", dest="email", metavar="EMAIL",
                      help=u"�û� email, �����ֻ���")
    parser.add_option("-p", "--pass", "--password",
                      action="store", type="string", dest="password", metavar="PASSWORD",
                      help=u"�û�����")
    parser.add_option("-e", "--enable",
                      action="append", dest="farmOption", metavar="TERM",
                      choices=['help-friends', 'sell-all', 'full-simulate', 'steal'], default=[],
                      help=u"������ TERM")
    parser.add_option("-d", "-no", "--disable",
                      action="append", dest="farmOptionDisable", metavar="TERM",
                      choices=['help-friends', 'sell-all', 'full-simulate', 'steal'], default=[],
                      help=u"�ر����� TERM �����ȼ�")
    (options, args) = parser.parse_args()

    for op in options.farmOption:
        defaultConfig[op] = True
    for op in options.farmOptionDisable:
        defaultConfig[op] = False
    defaultConfig['cache-file'] = options.cacheFile
    # set logging
    print "��־д�뵽 %s." % options.logfile 
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y %b %d %H:%M:%S',
                        filename = options.logfile,
                        filemode='a')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', '%H:%M:%S')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    logging.info("================ �������� ==================")
    h = HappyFarm(options.email, options.password)
    logging.info("ִ�� runSimple ����.")
    h.runSimple()
    h.logProfit()
