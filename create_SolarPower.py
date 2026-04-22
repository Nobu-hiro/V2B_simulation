import pandas as pd
import datetime
import numpy as np
import os

class get_solarpowerdata():
    def __init__(self):
        self.Dict_DF={}
        pass
    
    def get_solar_radiation(self,start_date,period_year):
        InputFolder = "solar_radiation_data"
        list_data = os.listdir(InputFolder)
        Dict_DF={}
        for file in list_data:
            df = pd.read_csv(InputFolder+"/"+file,skiprows=1,header=None)
            info = pd.read_csv(InputFolder+"/"+file,nrows=1,header=None)
            df.columns=["ID","Month","Day","Year",0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,"","","","",""]
            List_DF=[]
            for i in range(1,4):
                df_s = df.loc[df["ID"]==i,range(0,24)].stack()
                dt_list = pd.date_range(start=start_date, periods=period_year*365*24, freq='1h')
                df_s.index = dt_list
                List_DF.append(df_s)
            DF = pd.concat(List_DF,axis=1)
            DF.columns=["H","Hb","Hd"]
            DF["Num_Data"]=(DF.index.date - datetime.date(2022,1,1))/datetime.timedelta(days=1)+1
            DF["Place"]=info.values[0,1]
            DF["phai"]=info.values[0,2]
            DF["gamma"]=info.values[0,4]
            DF["Sum_radiation"]=DF["H"].sum()
            Dict_DF[info.values[0,1]]=DF
        self.Dict_DF=Dict_DF
        
    
    def get_solar_power_timeseries(self,place):
        DF_Power=self.Dict_DF[place].apply(self.get_solar_power,axis=1)
        return(DF_Power)
    
    def get_solar_power(self,df):
        #JIS C 8907:2005 太陽光発電システムの発電電力量推定方法
        #Ep=Ｋ_d ×　ＫPT　×　Ｐ　×　H　÷　Ｇ
        """
        ・太陽電池アレイ設置方式による加重平均温度上昇：21.5℃ （屋根置き形（折板設置含む））
        ・太陽電池モジュールの最大出力温度係数（αPmax）は、太陽電池モジュールの型式毎に若干異なります。
        ・基準状態の太陽電池モジュール温度（JIS C 8913より）：25℃
        ・基本設計係数 K'：0.926（総合設計係数から温度補正係数、インバータ回路補正係数を除いたもの）
        ・インバータ回路補正係数（実効効率）は、パワーコンディショナ変換効率（定格負荷時）の係数で代用しています。使用パワーコンディショナ：PVN-553（96.0%）
        ③太陽電池設置条件は、傾斜角30°、方位角： 0°（真南）、一面設置で算出しています。
        """
        place = df["Place"]
        phai = df["phai"]/360*2*np.pi
        gamma = df["gamma"]/360*2*np.pi
        KWH = 0.277778 #MJ->kWh
        H = df["H"]*0.01*KWH #kWh
        Hb = df["Hb"]*0.01*KWH  #kWh
        Hd = df["Hd"]*0.01*KWH  #kWh
        Sum_radiation = df["Sum_radiation"]*0.01
        num_date = df["Num_Data"]
        Ts = df.name.hour
        
        Kd = 0.7562
        aPmax = 0.5#最大出力温度係数（結晶系）
        TAV = 25#月平均気温
        theta_a = 30/360*2*np.pi
        delta_T = 21.5
        TCR = TAV+delta_T
        KPT = 1 + aPmax*(TCR-25)/100#温度補正係数
        P = 1
        HH = self.Inclined_solar_radiation(theta_a,phai,gamma,H,Hb,Hd,num_date,Ts) #kWh
        G = 1
        #Ep = Kd * KPT * P * HH  / G
        Ep = H / Sum_radiation * 1000 * P*5#計算方法要確認
        if Ep > 1:
            Ep = 1
        elif Ep<0:
            Ep = 0
        return(Ep)
    
    def Inclined_solar_radiation(self,theta_a,phai,gamma,H,Hb,Hd,num_date,Ts):
        t = self.hour_anlge(num_date,gamma,Ts)
        delta = self.delta(num_date)
        
        cos_theta = self.cos_theta(theta_a,phai,gamma,t,delta)
        cos_theta_z= self.cos_theta_z(phai,gamma,t,delta)
        ratio = cos_theta/cos_theta_z
        if ratio>2:
            ratio = 1
            
        
        p = 0.2
        #斜面直達日射量（直接法モデル）
        hb = Hb*ratio
        #斜面反射日射量（均一反射モデル）
        hr = H*p*(1 - np.cos(theta_a))/ 2
        #斜面散乱日射量（等方性モデル）
        hd = Hd *(1 + np.cos(theta_a)) / 2
        #斜面日射量はこれらの和で
        h = hb + hr + hd
        return(h)
    
    def cos_theta(self,theta_a,phai,gamma,t,delta):
        cos_theta =(np.sin(phai)*np.cos(theta_a)-np.cos(phai)*np.sin(theta_a)*np.cos(gamma))*np.sin(delta)+(np.cos(phai)*np.cos(theta_a)+np.sin(phai)*np.sin(theta_a)*np.cos(gamma))*np.cos(delta)*np.cos(t)+np.cos(delta)*np.sin(theta_a)*np.sin(gamma)*np.sin(t)        
        return(cos_theta)
    
    def cos_theta_z(self,phai,gamma,t,delta):
        cos_theta_z = np.sin(phai)*np.sin(delta)+np.cos(phai)*np.cos(delta)*np.cos(t)
        return(cos_theta_z)
    
    def delta(self,num_date):
        ω = 2*np.pi/365
        J =  num_date + 0.5
        delta = 0.33281 - 22.984*np.cos(ω*J) - 0.34990*np.cos(2*ω*J) - 0.13980*np.cos(3*ω*J)+ 3.7872*np.sin(ω*J) + 0.03250* np.sin(2*ω*J) + 0.07187*np.sin(3*ω*J)
        delta = delta/360*2*np.pi
        return(delta)
    
    def hour_anlge(self,num_date,gamma,Ts):
        e = self.equation_of_time(num_date)
        T = Ts + (gamma/(2*np.pi)*360 - 135)/15 + e
        t = 15*T - 180
        t = t/360*2*np.pi
        return(t)
        
    def equation_of_time(self,num_date):
        ω = 2*np.pi/365
        J =  num_date + 0.5
        e = 0.0072*np.cos(ω*J) - 0.0528*np.cos(2*ω*J) - 0.0012*np.cos(3*ω*J)- 0.1229*np.sin(ω*J) - 0.1565*np.sin(2*ω*J) - 0.0041*np.sin(3*ω*J)
        return(e)
