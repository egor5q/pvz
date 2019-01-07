# -*- coding: utf-8 -*-
import os
import telebot
import time
import random
import threading
from emoji import emojize
from telebot import types
from pymongo import MongoClient


token = os.environ['TELEGRAM_TOKEN']
bot = telebot.TeleBot(token)


client=MongoClient(os.environ['database'])
db=client.pvz
users=db.users

games={}
inbattle=[]

plantstats={                           # Тип "wall" обозначает, что зомби будут атаковать его;
    'pea':{'dmg':1,                    # Тип "attacker" обозначает, что растение атакует.
           'name':'pea',
           'hp':5,
           'range':100,
           'skills':[],
           'types':['plant','attacker','wall'],
           'cost':10,
           'effects':[]
          },
    
    'sunflower':{'hp':5,
                 'name':'sunflower',
                 'skills':['sungen'],
                 'types':['plant','wall'],
                 'storage':100,
                 'cost':100,
                 'effects':[]
                },
    
    'wallnut':{'hp':50,
               'name':'wallnut',
               'skills':[],
               'types':['plant','wall'],
               'cost':20,
               'effects':[]
              },
    
    'mine':{'dmg':50,
            'name':'mine',
            'skills':['mine'],
            'types':['plant'],
            'cost':12,
            'effects':[]
           }
}

zombiestats={
    'simple':{'hp':8,
              'name':'simple',
              'dmg':3,
              'speed':10,
              'skills':[],
              'types':['zombie'],
              'cost':10,
              'effects':[]
             },
    'cone':{'hp':12,
            'name':'cone',
            'dmg':3,
            'speed':10,
            'skills':[],
            'types':['zombie'],
            'cost':15,
            'effects':[]
           }
}
            

    
    
em_plants={
    'pea':'🔵', 
    'sunflower':'🌻', 
    'wallnut':'🌰',
    'mine':'🥔'
}

allplants=[
        'pea',
        'sunflower',
        'wallnut',
        'mine'
]

plantnames={
    'pea':'Горохострел',
    'sunflower':'Подсолнух',
    'wallnut':'Стенорех',
    'mine':'Картофельная мина'
}
    
@bot.message_handler(commands=['testattack'])
def testattack(m):
    if m.from_user.id==441399484:
        user=users.find_one({'id':m.from_user.id})
        randomattack(user)
    
def randomattack(user):
    if user['garden-lvl']==1:
        players=[]
        players.append(createplayer(user))
        zombies=[]
        s=0
        c=0
        while s<random.randint(2,4):
            zombies.append('simple')
            s+=1
        while c<random.randint(0,2):
            zombies.append('cone')
            c+=1
        games.update(creategame(players,'pve',zombies,user['glenght'],user['id']))
        startgame(games[user['id']])
        
    
def startgame(game):
    zombies=[]
    n=0
    if len(game['zombies'])>5:
        i=5
    else:
        i=len(game['zombies'])
    while n<i:
        #тут пойдёт расстановка 5ти или меньше зомбей по 5 лайнам, рандомно.
        z=random.choice(game['zombies'])
        zombies.append(z)
        game['zombies'].remove(z)
        n+=1
    lines=[1,2,3,4,5]
    for ids in zombies:
        line=random.choice(lines)
        lines.remove(line)
        game['activezombies'].append(createzombie(ids,line,game['glenght']+1))
    if game['turn']==1:    
        for ids in game['players']:
            sendm(ids['id'],'Ваш сад атакуют зомби! Дальше я буду отправлять вам отчёт о битве...')
            
    if game['turn']==1:
        i=1
        while i<=5:
            p=1
            while p<=game['glenght']:
                x=plantt(game['garden'][str(i)+'line'][str(p)+'pos'])
                if x!=None:
                    game['garden'][str(i)+'line'][str(p)+'pos']=x.copy()
                p+=1
            i+=1 
    
    for ids in game['activezombies']:
        zombie=ids
        if 'die' not in zombie['effects']:
            zombieact(zombie, game)
    i=1
    while i<=5:
        p=1
        while p<=game['glenght']:
            plant=game['garden'][str(i)+'line'][str(p)+'pos']
            if plant!=None:
                if 'die' not in plant['effects']:
                    plantact(plant,i,p,game)
            p+=1
        i+=1
        
    endturn(game)
  

def allplantchoice(act):
    i=1
    while i<=5:
        p=1
        while p<=game['glenght']:
            act
            p+=1
        i+=1

def endturn(game):
    for ids in game['activezombies']:
        zombie=ids
        if zombie['hp']<=0:
            zombie['effects'].append('die')
            
    i=1
    while i<=5:
        p=1
        while p<=game['glenght']:
            plant=game['garden'][str(i)+'line'][str(p)+'pos']
            if plant['hp']<=0:
                plant['effects'].append('die')
            p+=1
        i+=1
    
    for ids in game['players']:
        sendm(game['players'][ids]['id'], game['res'])
    game['turn']+=1
    t=threading.Timer(5,startgame,args=[game])
    t.start()
        
        
def plantt(plant):
    if plant!=None:
        plant=plantstats[plant]
        return plant
    else:
        return None
    
    
    
def plantact(plant,line,pos,game):
    if 'attacker' in plant['types']:
        i=pos
        target=None
        while i<=game['glenght'] and target==None:
            for ids in game['activezombies']:
                zombie=ids
                if zombie['garden']['line']==line and zombie['garden']['pos']==pos and 'die' not in zombie['effects']:
                    target=zombie
            i+=1
        if target!=None:
            target['hp']-=plant['dmg']
            game['res']+='🍃|Растение атакует зомбя на '+str(line)+' линии!\n'
        else:
            game['res']+='🍃|Растение стоит АФК на '+str(line)+' линии!\n'
        
def zombieact(zombie, game):
    line=zombie['garden']['line']
    pos=zombie['garden']['pos']
    if zombie['garden']['pos']>game['glenght']:
        move(zombie,line,pos,game)
       
    else:
        cplant=game['garden'][str(line)+'line'][str(pos)+'pos']
        if cplant!=None:
            if 'wall' in cplant['types'] and 'die' not in cplant['effects']:
                attack(zombie,line,pos,game)
            else:
                move(zombie,line,pos,game)
        else:
            move(zombie,line,pos,game)
        
def attack(unit,line,pos,game):
    cenemy=game['garden'][str(line)+'line'][str(pos)]
    if cenemy!=None:
        cenemy['hp']-=unit['dmg']
        if 'zombie' in unit['types']:
            game['res']+='🧟‍♂️|Зомби атакует растение на '+str(line)+' линии!\n'
        elif 'plant' in unit['types']:
            game['res']+='🍃|Растение атакует зомбя на '+str(line)+' линии!\n'
        
def move(zombie,line,pos,game):
    x=int(zombie['speed']/10)
    pos-=x
    game['res']+='🧟‍♂️|Зомби двигается по линии '+str(line)+' на '+str(pos)+' позицию!\n'
    

def zombattack():
    x=users.find({})
    for ids in x:
        if ids['rest']>=60 and random.randint(1,100)<=20:
            randomattack(ids)
    
@bot.message_handler(commands=['start'])
def start(m):
    id=m.from_user.id
    name=m.from_user.first_name
    username=m.from_user.username
    chatid=m.chat.id
    if id==chatid:
        if users.find_one({'id':id})==None:
            users.insert_one(createuser(id,name,username))
            sendm(chatid, 'Здраствуй, боец! В этой игре ты будешь сажать растения и оборонять свой сад от армий '+
                             'зомби, которые хотят съесть твои мозги. Также тебе предстоит избавляться от конкурентов-садоводов, '+
                             'насылая на них своих зомби. Доступные на данный момент режимы игры:\n'+
                             '*PvP (wait...)*\n*PvE(wait...)*\n*Постоянная защита сада (coding...)*\n'+
                             'Удачи!\n\n',parse_mode='markdown')
 
@bot.message_handler(commands=['sendzombie'])
def sendzombie(m):
    id=m.from_user.id
    name=m.from_user.first_name
    username=m.from_user.username
    chatid=m.chat.id
    if id==chatid:
        sendm(id, 'Выберите зомби (одного или нескольких) для атаки случайного вражеского сада.')

def menu1(id,calldata=None,callid=None):
    text='Общая картина сада:\n'
    x=users.find_one({'id':id})
    i=1
    while i<=5:
        z=1
        text+=str(i)+' линия:| '
        while z<=x['glenght']:
            text+=planttoemoji(x['garden-plants'][str(i)+'line'][str(z)+'pos'])+'   '
            z+=1
        text+='\n\n'
        i+=1
        
    kb=types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text='1 линия',callback_data='1 line'))
    kb.add(types.InlineKeyboardButton(text='2 линия',callback_data='2 line'))
    kb.add(types.InlineKeyboardButton(text='3 линия',callback_data='3 line'))
    kb.add(types.InlineKeyboardButton(text='4 линия',callback_data='4 line'))
    kb.add(types.InlineKeyboardButton(text='5 линия',callback_data='5 line'))
    if calldata==None:
        sendm(id,text+'Выберите линию для просмотра:',reply_markup=kb)
    else:
        medit(text+'Выберите линию для просмотра:',id,callid,reply_markup=kb)
    
    
def menu2(id,calldata,x,callid):
    kb=types.InlineKeyboardMarkup()
    n=calldata.split(' ')[0]
    text='Текущая линия: '+n+'\n'
    i=1
    while i<=x['glenght']:
        text+=str(i)+': '+planttoname(x['garden-plants'][n+'line'][str(i)+'pos'])+'\n'
        kb.add(types.InlineKeyboardButton(text=str(i)+' позиция',callback_data=str(i)+' pos '+n+' l'))
        i+=1
    kb.add(types.InlineKeyboardButton(text='Назад',callback_data='menu1'))
    medit(text,id,callid,reply_markup=kb)
    
def menu3(id,calldata,x,callid):
    kb=types.InlineKeyboardMarkup()
    L=calldata.split(' ')[2]
    P=calldata.split(' ')[0]
    text='Текущая линия: '+L+'\n'+\
    'Выберите растение для установки на '+P+' позицию:'
    n=0
    while n<len(allplants):
        count=x['storage-plants'][allplants[n]]
        if count>0:
            kb.add(types.InlineKeyboardButton(text=planttoname(allplants[n])+': '+str(count),callback_data='set '+allplants[n]+' '+L+' l '+P+' p'))
        n+=1
    kb.add(types.InlineKeyboardButton(text='Назад',callback_data=L+' l menu2'))
    medit(text,id,callid,reply_markup=kb)


def menu4(id,calldata,x,callid):
    kb=types.InlineKeyboardMarkup()
    plant=calldata.split(' ')[1]
    L=calldata.split(' ')[2]
    P=calldata.split(' ')[4]
    if x['storage-plants'][plant]>0:
        text='Вы успешно посадили растение "'+planttoname(plant)+'" на '+P+' позицию '+L+' линии!'
        cplant=x['garden-plants'][L+'line'][P+'pos']
        if cplant!=None:
            users.update_one({'id':id},{'$inc':{'storage-plants.'+cplant:1}})
        users.update_one({'id':id},{'$set':{'garden-plants.'+L+'line.'+P+'pos':plant}})
        users.update_one({'id':id},{'$inc':{'storage-plants.'+plant:-1}})
        medit(text,id,callid,reply_markup=kb)
        menu3(id,calldata,x,callid)
    
@bot.message_handler(commands=['garden'])
def garden(m):
    id=m.from_user.id
    name=m.from_user.first_name
    username=m.from_user.username
    chatid=m.chat.id
    if id==chatid:
        x=users.find_one({'id':id})
        if x!=None:
            menu1(id)
        
    
@bot.callback_query_handler(func=lambda call:True)
def inline(call): 
    kb=types.InlineKeyboardMarkup()
    id=call.from_user.id
    x=users.find_one({'id':id})
    if 'line' in call.data:
        menu2(id,call.data,x,call.message.message_id)
    
    if 'pos' in call.data:
        menu3(id,call.data,x,call.message.message_id)
        
    if 'set' in call.data:
        menu4(id,call.data,x,call.message.message_id)
        
    if call.data=='menu1':
        menu1(id,call.data,call.message.message_id)
        
    if 'menu2' in call.data:
        menu2(id,call.data,x,call.message.message_id)
        

    
def planttotext(x):
    return plantnames[x]
    
        
def planttoname(x):
    if x==None:
        return 'Пусто'
    else:
        return em_plants[x]+planttotext(x)
    
def planttoemoji(x):
    if x==None:
        return '__'
    else:
        return em_plants[x]
 

def sendm(id,text,parse_mode=None,reply_markup=None):
    bot.send_message(id,text,parse_mode=parse_mode,reply_markup=reply_markup)
       
def medit(message_text,chat_id, message_id,reply_markup=None,parse_mode=None):
    return bot.edit_message_text(chat_id=chat_id,message_id=message_id,text=message_text,reply_markup=reply_markup,
                                 parse_mode=parse_mode)       
        
def createuser(id,name,username):
    baseplants=['pea','sunflower','wallnut','mine']
    pos={'1pos':None,'2pos':None,'3pos':None,'4pos':None,'5pos':None}
    gplants={'1line':pos,'2line':pos,'3line':pos,'4line':pos,'5line':pos}
    i=len(allplants)
    n=0
    splants={}
    while n<i:
        splants.update({allplants[n]:0})
        n+=1
        print(splants)
    return{
        'id':id,
        'name':name,
        'username':username,
        'sun':0,
        'brains':0,
        'money':0,
        'zombies':[],
        'shop-plants':baseplants,
        'garden-plants':gplants,
        'storage-plants':splants,
        'glenght':5,
        'garden-lvl':1
        
    }

def createplayer(user):
    lines={'1':1,
           '2':1,
           '3':1,
           '4':1,
           '5':1
          }
    return {
        'garden':user['garden-plants'],
        'lines':lines,
        'id':user['id']
    }


def createzombie(name,line,pos):
    zombie=zombiestats[name].copy()
    x={'garden':{'line':line,
                 'pos':pos
                }
      }
    zombie.update(x)
    return zombie


def creategame(playerlist,gtype,zombies,lenght,id):
    return {id:{
        'type':gtype,
        'players':playerlist,
        'zombies':zombies,
        'activezombies':[],
        'garden':playerlist[0]['garden'],
        'glenght':lenght,
        'res':'',
        'turn':1
    }
    }

if True:
   print('7777')
   bot.polling(none_stop=True,timeout=600)

