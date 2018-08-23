#!/usr/bin/env python
# coding=utf-8


import numpy as np
import json, copy, os, multiprocessing
from multiprocessing import *
from multiprocessing.managers import BaseManager


# 分布式队列密集计算，客户端
class Client:
    getnumbertype = ['h', 't', 'o', 'j', 'a']
    # 原始49个数字序列
    origindataseq = np.arange(1, 50)
    # 输出最大值，当组合计算超过这个值，便打印输出
    outprintmaxvalue = 60.25
    # 实际最大值，当所有组合计算中超过这个值，便停止子线程计算，依次顺序为 波色 | 头数 | 尾数 | 单双 
    stopmaxvalue = [90.25, 92.25, 90.47, 82.15]
    # 公式使用类型(波色16+1个一组 | 头数10+1个一组 | 尾数4+1个一组 | 单双24+1个一组)
    formulatype = ['killcolor', 'killhead', 'killtail', 'killsingleordouble']
    # new ----> server config
    # serverip = '61.152.104.186'
    serverip = '127.0.0.1'
    serverport = 1213
    serverauth = bytes('a.j2JI)', 'utf8')

    def __init__(self):
        # 预读需要访问的数据，减少IO频率
        self.data = AllData.__data__()
        self.sortdata = AllData.__sortdata__()
        msdata = MarksixData()
        self.marksixdata = {"tail_number_data": msdata.tail_number_data,
                            "single_or_double_data": msdata.single_or_double_data,
                            "head_number_data": msdata.head_number_data,
                            "color_data": msdata.color_data,
                            "zodiacsequence": msdata.zodiacsequence()}
        pass

    def do(self):
        BaseManager.register('get_dispatched_sequence_queue', callable=self.get_dispatched_sequence_queue)
        BaseManager.register('get_finished_sequence_queue', callable=self.get_dispatched_sequence_queue)
        manager = BaseManager(address=(self.serverip, self.serverport), authkey=self.serverauth)
        manager.connect()

        # 使用上面注册的方法获取队列
        get_dispatched_sequence_queue = manager.get_dispatched_sequence_queue()
        get_finished_sequence_queue = manager.get_finished_sequence_queue()

        while True:
            try:
                expression = get_dispatched_sequence_queue.get(timeout=5)
                print('pid is [' + str(os.getpid()) + '], get content: %s ' % expression)
                # get_dispatched_sequence_queue.task_done()
                get_finished_sequence_queue.put(self.kill_anyaone_formula(expression, 'killtail'))
            except Exception as ex:
                print(ex)
                break
                
        print('handle completed')

    def kill_anyaone_formula(self, fr, formulakilltype):
        mosthighrate = 0
        returndata = {}
        count = 0
        r = 0
        joslen = -1
        for jo in range(len(self.data)):
            nextIndex = 0
            for index in range(len(self.data[jo])):
                count += 1
                joslen += 1
                nextIndex += 1
                killnextseq = []
                if nextIndex >= len(self.data[jo]):
                    break
                if fr["sort"] == 'size':
                    total = self.formula_expression_hander(fr["expression"],
                                                           self.sortdata[jo][index]) + fr["offset"]
                else:
                    total = self.formula_expression_hander(fr["expression"],
                                                           Common.get_number(self.data[jo][index])) + fr["offset"]

                nextnumber = int(self.data[jo][nextIndex][1]['unusual_number']['number'])  # 下期特码

                # if formulakilltype == self.formulatype[0]:
                #     # kill color
                #     killnext = str(Common.color(total))  # 下期要杀的颜色
                #     killnextseq = Common.getnumber(killnext, 'c')  # 获取杀颜色的序列
                #     pass
                # if formulakilltype == self.formulatype[1]:
                #     # kill head
                #     killnext = str(Common.head(total))  # 下期要杀的头数
                #     killnextseq = Common.getnumber(killnext, 'z')  # 获取杀头数的序列
                #     pass
                if formulakilltype == self.formulatype[2]:
                    killnextseq = Common.getnumber(self.marksixdata, str(Common.tail(total)), 't')
                # if formulakilltype == self.formulatype[3]:
                #     # kill single or double
                #     killnext = str(Common.singleordouble(total))  # 下期要杀的单双
                #     killnextseq = Common.getnumber(killnext, 't')  # 获取杀单双的序列
                #     pass

                # noinspection PyBroadException
                try:
                    if nextnumber in list(set(self.origindataseq) - (set(killnextseq))):
                        r += 1
                except:
                    pass

            # 当前执行正确率
        mathrate = round((r / (joslen - 1)) * 100.0, 3)

        if mathrate > mosthighrate:
            mosthighrate = mathrate
            returndata['rat'] = mosthighrate
            returndata['exp'] = fr
            returndata['pid'] = os.getpid()
        return returndata

    def formula_expression_hander(self, formulaexpression, matharray):
        fexpressionarray = formulaexpression.split(' ')
        newmatharray = []
        index = 0
        for f in fexpressionarray:
            numIndex = int(f[0])
            operator = f[1]
            if operator == self.getnumbertype[0]:  # 头
                newmatharray.append(int(str(matharray[numIndex]).zfill(2)[0]))
            if operator == self.getnumbertype[1]:  # 尾
                newmatharray.append(int(str(matharray[numIndex]).zfill(2)[1]))
            if operator == self.getnumbertype[2]:  # 原
                newmatharray.append(int(matharray[numIndex]))
            if operator == self.getnumbertype[3]:  # 合 
                newmatharray.append(
                    int(str(matharray[numIndex]).zfill(2)[0]) + int(
                        str(matharray[numIndex]).zfill(2)[1]))
            if operator == self.getnumbertype[4]:  # 积 
                newmatharray.append(
                    int(str(matharray[numIndex]).zfill(2)[0]) * int(
                        str(matharray[numIndex]).zfill(2)[1]))
            index += 1
            pass
        return sum(newmatharray)

    def get_dispatched_sequence_queue(self):
        return self.dispatched_sequence_queue

    def get_finished_sequence_queue(self):
        return self.finished_sequence_queue


class Common(object):
    @staticmethod
    def color(t):
        """
        波色
        :param t: 
        :return: 
        """
        if t % 3 + 1 == 1:
            return '红'
        elif t % 3 + 1 == 2:
            return '蓝'
        elif t % 3 + 1 == 3:
            return '绿'

    @staticmethod
    def tail(t):
        """
        尾
        :param t: 
        :return: 
        """
        return t % 10

    @staticmethod
    def singleordouble(o):
        """
        单双
        :param o: 
        :return: 
        """
        if int(o) % 2 == 0:
            return '双'
        else:
            return '单'

    @staticmethod
    def head(t):
        """
        头
        :param t: 
        :return: 
        """
        return t % 5

    @staticmethod
    def _print(s):
        sys.stdout.write("\r" + str(s))
        sys.stdout.flush()

    # noinspection PyBroadException
    @staticmethod
    def getnumber(data, o, t):
        """
        获取制定类型的序列
        :param o: 头 | 尾 | 肖 | 色 | 单 五种类型的数据  
        :param t: h | t | z | c | s
        :return: 
        """
        if t == "z":
            _Common__zodiac = data['zodiacsequence']
            for z in _Common__zodiac:
                for zz in _Common__zodiac[z]:
                    if o == zz:
                        return _Common__zodiac[z][zz]['Sequence']
        elif t == "h":
            _Common_head = data['head_number_data']
            for h in _Common_head:
                try:
                    if o == '0':
                        if h.index(int(1)) > -1:
                            return h
                    if h.index(int(o + '0')) > -1:
                        return h
                except:
                    pass
            pass
        elif t == "t":
            for tt in data['tail_number_data']:
                if o == '0':
                    o = '1' + o
                if int(o) in tt:
                    return tt
        elif t == "c":
            if o == "红":
                return data['color_data'][0]
            elif o == "蓝":
                return data['color_data'][1]
            elif o == "绿":
                return data['color_data'][2]
            pass
        elif t == "s":
            if o == '双':
                return data['single_or_double_data'][1]
            else:
                return data['single_or_double_data'][0]

    @staticmethod
    def writefile(y, s):
        fo = open(os.getcwd() + "/" + str(y) + ".txt", 'w', encoding='utf8')
        fo.write(s)
        fo.close()

    @staticmethod
    def get_number(o):
        # 获取每个号码
        sixnumber = o[1]['six_number']
        unusualnum = o[1]['unusual_number']
        # 按照掉球排序
        n01 = sixnumber['1']['number']
        n02 = sixnumber['2']['number']
        n03 = sixnumber['3']['number']
        n04 = sixnumber['4']['number']
        n05 = sixnumber['5']['number']
        n06 = sixnumber['6']['number']
        n07 = unusualnum['number']
        return [n01, n02, n03, n04, n05, n06, n07]


class MarksixData(object):
    # 十二生肖集合（固定）
    zodiacs = ['鼠', '牛', '虎', '兔',
               '龙', '蛇', '马', '羊',
               '猴', '鸡', '狗', '猪']

    # 反十二生肖集合（固定）
    r_zodiac = ['猪', '狗', '鸡', '猴',
                '羊', '马', '蛇', '龙',
                '兔', '虎', '牛', '鼠']

    # 波色集合（固定）
    color_data = [
        # 红
        [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46],
        # 蓝
        [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48],
        # 绿
        [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49]
    ]

    # 头数集合（固定）
    head_number_data = [
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
        [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        [20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
        [30, 31, 32, 33, 34, 35, 36, 37, 38, 39],
        [40, 41, 42, 43, 44, 45, 46, 47, 48, 49],
    ]

    # 尾数集合（固定）
    tail_number_data = [
        [10, 20, 30, 40],
        [1, 11, 21, 31, 41],
        [2, 12, 22, 32, 42],
        [3, 13, 23, 33, 43],
        [4, 14, 24, 34, 44],
        [5, 15, 25, 35, 45],
        [6, 16, 26, 36, 46],
        [7, 17, 27, 37, 47],
        [8, 18, 28, 38, 48],
        [9, 19, 29, 39, 49]
    ]

    # 单双集合（固定）
    single_or_double_data = [
        # 单数
        [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47,
         49],
        # 双数
        [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48]
    ]

    # 尾数杀肖（固定）
    killzodiac = [
        {"0": "猪"},
        {"1": "狗"},
        {"2": "鸡"},
        {"3": "蛇"},
        {"4": "猪"},
        {"5": "猪"},
        {"6": "兔"},
        {"7": "马"},
        {"8": "鸡"},
        {"9": "牛"}
    ]

    def __init__(self, zodiacname='鸡'):
        self.zodiac = zodiacname

    def zodiacsequence(self):
        """
        十二生肖对应的不同号码集合
        :return: 
        """
        i = 0
        reversalZodiac = copy.deepcopy(self.r_zodiac)
        split = 0
        b = {}
        for z in self.zodiacs:
            if z == self.zodiac:
                split = i
            i = i + 1
        befor = (len(self.zodiacs) - split)
        i = 0
        for z in reversalZodiac:
            if i != befor:
                b[i] = z
            if i == befor:
                break
            i = i + 1
        for _ in b:
            del reversalZodiac[0]
        fast = b[len(b) - 1]
        del b[len(b) - 1]
        retZodiac = [fast]
        for z in reversalZodiac:
            retZodiac.append(z)
        for bb in b:
            retZodiac.append(b[bb])
        return {
            1: {retZodiac[0]:
                    {'Sequence': [1, 13, 25, 37, 49],
                     'Color': ['red', 'red', 'blue', 'blue', 'green']}},
            2: {retZodiac[1]:
                    {'Sequence': [2, 14, 26, 38], 'Color': ['red', 'blue', 'blue', 'green']}},
            3: {retZodiac[2]:
                    {'Sequence': [3, 15, 27, 39], 'Color': ['blue', 'blue', 'green', 'green']}},
            4: {retZodiac[3]:
                    {'Sequence': [4, 16, 28, 40], 'Color': ['blue', 'green', 'green', 'red']}},
            5: {retZodiac[4]:
                    {'Sequence': [5, 17, 29, 41], 'Color': ['green', 'green', 'red', 'blue']}},
            6: {retZodiac[5]:
                    {'Sequence': [6, 18, 30, 42], 'Color': ['green', 'red', 'red', 'blue']}},
            7: {retZodiac[6]:
                    {'Sequence': [7, 19, 31, 43], 'Color': ['red', 'red', 'blue', 'green']}},
            8: {retZodiac[7]:
                    {'Sequence': [8, 20, 32, 44], 'Color': ['red', 'blue', 'green', 'green']}},
            9: {retZodiac[8]:
                    {'Sequence': [9, 21, 33, 45], 'Color': ['blue', 'green', 'green', 'red']}},
            10: {retZodiac[9]:
                     {'Sequence': [10, 22, 34, 46], 'Color': ['blue', 'green', 'red', 'red']}},
            11: {retZodiac[10]:
                     {'Sequence': [11, 23, 35, 47], 'Color': ['green', 'red', 'red', 'blue']}},
            12: {retZodiac[11]:
                     {'Sequence': [12, 24, 36, 48], 'Color': ['red', 'red', 'blue', 'blue']}},
        }


class AllData(object):

    @staticmethod
    def __data__():
        c = '''
        '''
        return json.loads(c)

    @staticmethod
    def __sortdata__():
        sortdata = AllData.__data__()
        for jo in sortdata:
            for index in range(len(jo)):
                jsonlist = jo[index]
                sixnumber = jsonlist[1]['six_number']
                unusualnum = jsonlist[1]['unusual_number']
                n01 = sixnumber['1']['number']
                n02 = sixnumber['2']['number']
                n03 = sixnumber['3']['number']
                n04 = sixnumber['4']['number']
                n05 = sixnumber['5']['number']
                n06 = sixnumber['6']['number']
                n07 = unusualnum['number']
                lists = [n01, n02, n03, n04, n05, n06, n07]
                sortlist = AllData.bubble_sort(lists)
                jo[index] = sortlist
        return sortdata

    @staticmethod
    def bubble_sort(lists):
        # 大小排序（冒泡排序）
        count = len(lists)
        for i in range(0, count):
            for j in range(i + 1, count):
                if lists[i] < lists[j]:
                    lists[i], lists[j] = lists[j], lists[i]
        return lists


if __name__ == '__main__':
    for _ in range(multiprocessing.cpu_count()):
        Process(target=Client().do).start()