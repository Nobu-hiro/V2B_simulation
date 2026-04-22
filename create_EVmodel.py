#%%
import os
import pandas as pd
import numpy as np
import datetime
import random
from time import time
import pulp

import matplotlib.pyplot as plt
random.seed(314)
#%%
class EV():
    def __init__(self,ID,TripType,ChargeType):
        self.ID = ID
        self.TripType = TripType
        self.ChargeType = ChargeType

class EVDayTrip():
    def __init__(self,Region):
        self.Region = Region
        self.Dict_RegionCode={}
        self.Dict_RegionCode["All"]=100
        

        self.make_DayTrip()
        self.analyze_UserTypeRatio()
        print(self.Dict_UserTypeRatio)

    def cal_value(self,List_value, List_probability):
        r = np.random.rand()
        return(List_value[np.sum(List_probability<r)]) 
    
   
    
    def make_tripdist(self):

        df_TripDistance = pd.read_excel("TripDistance.xlsx",skiprows=2)
        df_TripDistance.columns = ["weekday_code","weekday","cartype_code","cartype","purpose_code","purpose","code_tripdist_rank","tripdist_rank","tripdist_count"]
        Dict_Tripdist ={}
        for Weekday in ["Weekday","Weekend"]:
            Dict_Tripdist[Weekday]={}
            for purpose in ["commute","return","private","office","service"]:
                Dict_Tripdist[Weekday][purpose]={}
                Tripdist_X = [1,3.5,7.5,12.5,17.5,25,65,125]
                if purpose =="commute":
                    purpose_code = 1
                elif purpose=="office":
                    purpose_code = 2
                elif purpose=="private":
                    purpose_code = 3
                elif purpose=="return":
                    purpose_code = 4
                elif purpose=="service":
                    purpose_code = 5
                elif purpose=="unknown":
                    purpose_code = 9
                else:
                    purpose_code = 10

                if Weekday == "Weekday":
                    weekday_code = 1
                else:
                    weekday_code = 2
                idx_tripdistance = (df_TripDistance["weekday_code"]==weekday_code)&(df_TripDistance["cartype_code"]==1)&(df_TripDistance["purpose_code"]==purpose_code)
                prob = df_TripDistance.loc[idx_tripdistance,"tripdist_count"][:-2]
                Tripdist_Y = prob.cumsum().values/prob.sum()
                Dict_Tripdist[Weekday][purpose]["TripDistance"] =  Tripdist_X
                Dict_Tripdist[Weekday][purpose]["TripDistProbability"] =  Tripdist_Y
        return(Dict_Tripdist)

    
    
    def make_triptime(self):
        df_TripHour = pd.read_excel("TripHour.xlsx",skiprows=2)
        df_TripHour.columns = ["purpose_code","purpose","code_triphour_rank","triphour_rank","triphour_count"]
        Dict_Triptime = {}
        for purpose in ["commute","return","private","office","service","unknown","all"]:
            Dict_Triptime[purpose]={}
            Triptime_X= [4.5,6.5,7.5,8.5,9.5,10.5,11.5,12.5,13.5,14.5,15.5,16.5,17.5,18.5,19.5,20.5,21.5,22.5,23.5,25.5]
            if purpose =="commute":
                purpose_code = 1
            elif purpose=="office":
                purpose_code = 2
            elif purpose=="private":
                purpose_code = 3
            elif purpose=="return":
                purpose_code = 4
            elif purpose=="service":
                purpose_code = 5
            elif purpose=="unknown":
                purpose_code = 9
            else:
                purpose_code = 10
            
            idx = df_TripHour["purpose_code"]==purpose_code
            Series_Triptime = df_TripHour.loc[idx,"triphour_count"][:-3]
            Triptime_Y=(Series_Triptime.cumsum()/Series_Triptime.cumsum().iloc[-1]).values   
            Dict_Triptime[purpose]["Triptime"]=Triptime_X
            Dict_Triptime[purpose]["TripTimeProbability"] = Triptime_Y
        return(Dict_Triptime)
    
    def make_tripcount(self,region_code=100):
        df_TripCount = pd.read_excel("TripCount.xlsx",skiprows=2)
        df_TripCount.columns = ["year","japanese_year","cartype_code","cartype","purpose_code","purpose","region_code","region","TripCount_Net","TripCount_Gross","TripRatio","Comment"]
        Dict_Tripcount = {}
        for purpose in ["commute","return","private","office","service"]:
            if purpose =="commute":
                purpose_code = 1
            elif purpose=="office":
                purpose_code = 2
            elif purpose=="private":
                purpose_code = 3
            elif purpose=="return":
                purpose_code = 4
            elif purpose=="service":
                purpose_code = 5
            elif purpose=="unknown":
                purpose_code = 9
            else:
                purpose_code = 10
            idx_tripcount = (df_TripCount["year"]==2021)&(df_TripCount["cartype_code"]==1)&(df_TripCount["purpose_code"]==purpose_code)&(df_TripCount["region_code"]==region_code)
            Dict_Tripcount[purpose]=df_TripCount.loc[idx_tripcount,"TripCount_Net"].values[0]
        return(Dict_Tripcount)
    
    def make_DayTrip(self):
        Dict_Tripdist = self.make_tripdist()
        Dict_Triptime = self.make_triptime()
        Dict_Tripcount = self.make_tripcount()
        Dict_NumDay = {}
        Dict_NumDay["Weekday"] = 1000
        Dict_NumDay["Weekend"] = 1000

        self.Dict_DayList = {}
        for key in Dict_NumDay.keys():
            self.Dict_DayList[key]={}
            self.Dict_DayList[key]["Commuter"]=[]
            self.Dict_DayList[key]["Service"]=[]
            self.Dict_DayList[key]["Private"]=[]
            self.Dict_DayList[key]["Office"]=[]

            count_day = 0
            while count_day < Dict_NumDay[key]:
                Is_Commuter = False
                Is_Service = False
                DayEvent = {}
                List_TripDistance = []
                List_Departuretime = []
                List_Purpose = []
                for purpose in ["service","commute","private","office"]:
                    #No count commute or office in weekend
                    if (key=="Weekend")&(purpose!="private"):continue
                    
                    TripCount = np.random.poisson(Dict_Tripcount[purpose],1)[0]
                    
                    #service count as not trip
                    if (purpose=="service")&(TripCount>0):
                        Is_Service = True
                    # classify the commuter
                    if (purpose=="commute")&(TripCount>1):continue
                    for count in range(TripCount):
                        List_TripDistance.append(self.cal_value(Dict_Tripdist[key][purpose]["TripDistance"],
                                                                Dict_Tripdist[key][purpose]["TripDistProbability"]))

                        List_Departuretime.append(self.cal_value(Dict_Triptime[purpose]["Triptime"],
                                                                 Dict_Triptime[purpose]["TripTimeProbability"]))
                        List_Purpose.append(purpose)
                    if (purpose=="commute")&(TripCount==1):
                        Is_Commuter = True
                        CommuterTrip = List_TripDistance[-1]
                purpose = "return"
                if Is_Commuter:
                    List_TripDistance.append(CommuterTrip)
                else:
                    List_TripDistance.append(self.cal_value(Dict_Tripdist[key][purpose]["TripDistance"],
                                                            Dict_Tripdist[key][purpose]["TripDistProbability"]))
                List_Departuretime.append(self.cal_value(Dict_Triptime[purpose]["Triptime"],
                                                        Dict_Triptime[purpose]["TripTimeProbability"]))
                List_Purpose.append(purpose)

                            
                DayEvent["TripDistance"] = [i for _, i in sorted(zip(List_Departuretime, List_TripDistance))]
                DayEvent["Purpose"] = [i for _, i in sorted(zip(List_Departuretime, List_Purpose))]
                DayEvent["Departuretime"] = sorted(List_Departuretime)
                if DayEvent["Purpose"][-1]!="return":continue
                if DayEvent["Purpose"][0]=="return":continue
                if Is_Service:
                    UserType="Service"
                    DayEvent["Base"]="Office"
                elif Is_Commuter:
                    UserType="Commuter"
                    DayEvent["Base"]="Home"
                elif "office" in DayEvent["Purpose"]:
                    UserType="Office"
                    DayEvent["Base"]="Office"
                else:
                    UserType="Private"
                    DayEvent["Base"]="Home"
                DayEvent["Destination"]=[]
                for purpose in DayEvent["Purpose"]:
                    if purpose=="commute":
                        DayEvent["Destination"].append("Office")
                    elif purpose == "private":
                        DayEvent["Destination"].append("Other")
                    elif purpose=="return":
                        DayEvent["Destination"].append(DayEvent["Base"])
                    else:
                        DayEvent["Destination"].append("Other")
                self.Dict_DayList[key][UserType].append(DayEvent)
                count_day += 1
    def analyze_UserTypeRatio(self):
        Dict_UserTypeRatio = {}

        for user in self.Dict_DayList["Weekday"].keys():
            Dict_UserTypeRatio[user] = len(self.Dict_DayList["Weekday"][user])
        TotalNum = sum(Dict_UserTypeRatio.values())
        for key in Dict_UserTypeRatio:
            Dict_UserTypeRatio[key]=Dict_UserTypeRatio[key]/TotalNum
        self.Dict_UserTypeRatio = Dict_UserTypeRatio


class EVTrip():
    def __init__(self,EV,EVDayTrip,StartTime,EndTime):
        self.EV =EV
        self.EV_TripDay = {}
        self.StartTime = StartTime
        self.EndTime =  EndTime
        self.TripDayRange = pd.date_range(start=self.StartTime,end=self.EndTime,freq='d')
        self.TRIPSPEED = 34 #km/h
        self.EVDayTrip = EVDayTrip

        self.Dict_RegionCode={}
        self.Dict_RegionCode["All"]=100

        self.Region = self.EVDayTrip.Region
        self.TripRatio = self.cal_TripRate(self.Dict_RegionCode[self.Region])
        

        #個別EVログ
        self.EV_Triphour={}
        self.EV_TripDay={}
        self.EV_Placehour={}
        self.EV_Energy={}   

        Dict_Base = {}
        Dict_Base["Commuter"]="Home"
        Dict_Base["Private"]="Home"
        Dict_Base["Office"]="Office"

        if EVDayTrip.Region!="All":
            self.TripType = random.choices(self.EVDayTrip.Dict_UserTypeRatio.keys(), k = 1, weights = self.EVDayTrip.Dict_UserTypeRatio.values())
        self.Base = Dict_Base[self.EV.TripType]

        self.cal_EVTrip()

    def cal_TripRate(self,region_code=100):
        df_TripRate = pd.read_excel("TripRatio.xlsx",skiprows=2)
        df_TripRate.columns = ["year","japanese_year","cartype_code","cartype","private_code","private","region_code","region","TripRatio","Comment"]
        idx_triprate = (df_TripRate["year"]==2021)&(df_TripRate["cartype_code"]==1)&(df_TripRate["private_code"]==10)&(df_TripRate["region_code"]==region_code)
        TripRatio = df_TripRate.loc[idx_triprate,"TripRatio"].values[0]/100
        return(TripRatio)

    def cal_EVTrip(self):
        if self.EV.TripType=="Commuter":
            CommuteDay = np.random.choice(self.EVDayTrip.Dict_DayList["Weekday"]["Commuter"])

        for day in  self.TripDayRange:
            TotalTripDistance = 0
            Is_WeekEnd = day.weekday()>=5
            if Is_WeekEnd:
                Weekday = "Weekend"
            else:
                Weekday = "Weekday"

            ID = self.EV.ID
            self.EV_TripDay[day]={}
            self.EV_TripDay[day]["Is_Trip"]=[]
            self.EV_TripDay[day]["TripDistance"] = []
            self.EV_TripDay[day]["Departuretime"] = []
            self.EV_TripDay[day]["Destination"]=[]
            if Is_WeekEnd&(self.EV.TripType=="Office"):
                Is_Trip = False
            else:
                Is_Trip = random.random()<self.TripRatio
            self.EV_TripDay[day]["Is_Trip"].append(Is_Trip)
            if Is_Trip:
                if Is_WeekEnd:
                    self.EV_TripDay[day] = np.random.choice(self.EVDayTrip.Dict_DayList[Weekday]["Private"])
                else:
                    if self.EV.TripType=="Commuter":
                        self.EV_TripDay[day] = CommuteDay
                    else:
                        self.EV_TripDay[day] = np.random.choice(self.EVDayTrip.Dict_DayList[Weekday][self.EV.TripType])

            if day == self.StartTime:
                hour = 0
            else:
                hour = 3   
            Place = self.Base

            if len(self.EV_TripDay[day]["Departuretime"])==0:
                while hour <=27:
                    dttime = day + datetime.timedelta(hours=1)*hour
                    self.EV_Triphour[dttime]=0
                    self.EV_Placehour[dttime]=Place
                    hour +=1
            for i in range(len(self.EV_TripDay[day]["Departuretime"])):
                Dep_TripTime = self.EV_TripDay[day]["Departuretime"][i]
                TripDistance = self.EV_TripDay[day]["TripDistance"][i]
                Destination = self.EV_TripDay[day]["Destination"][i]
                Last_TripDistance = TripDistance
                TotalTripDistance += TripDistance
                while hour <Dep_TripTime:
                    dttime = day + datetime.timedelta(hours=1)*hour
                    self.EV_Triphour[dttime] = 0
                    self.EV_Placehour[dttime] = Place
                    hour +=1
                    if hour >27:break
                while Last_TripDistance>0:
                    dttime = day + datetime.timedelta(hours=1)*hour
                    self.EV_Triphour[dttime]=min(self.TRIPSPEED,Last_TripDistance)
                    self.EV_Placehour[dttime]="Trip"
                    Last_TripDistance = max(Last_TripDistance-self.TRIPSPEED,0)
                    hour +=1
                    if hour >27:break
                dttime = day + datetime.timedelta(hours=1)*hour
                self.EV_Placehour[dttime]=Destination
                Place = Destination
                hour +=1
                if Place == self.Base:
                    self.EV_Triphour[dttime]=TotalTripDistance
                    TotalTripDistance = 0
                else:
                    self.EV_Triphour[dttime]=0

            while hour<=27:
                dttime = day + datetime.timedelta(hours=1)*hour
                self.EV_Triphour[dttime]=0
                self.EV_Placehour[dttime]=Place
                hour +=1

class EVGroupTrip():
    def __init__(self,Region,Num_EV,TripType,ChargeType,StartTime,EndTime,Annual_TripDistance=6780.71):
        self.Region = Region
        self.Num_EV = Num_EV
        self.TripType = TripType
        self.ChargeType = ChargeType
        self.StartTime = StartTime
        self.EndTime = EndTime
        self.Annual_TripDistance = Annual_TripDistance
        self.Model_TripDistance = 6780.71
        self.List_EV=[]
        self.Dict_EVTrip={}
        self.TripHourRange =  pd.date_range(start=self.StartTime,end=self.EndTime,freq='h')
        self.n_range=len(self.TripHourRange)
        self.TripRatio = self.Annual_TripDistance/self.Model_TripDistance
        self.EVGroupTriphour=np.zeros(self.n_range)
        self.NumHomehour = np.zeros(self.n_range)
        self.NumOfficehour = np.zeros(self.n_range)
        self.NumOtherhour = np.zeros(self.n_range)
        self.NumTriphour = np.zeros(self.n_range)
        self.NumBASEhour = np.zeros(self.n_range)
        self.Energyhour=np.zeros(self.n_range)

        self.set_EV()
        self.EVDayTrip = EVDayTrip("All")
        self.cal_EVtrip()
        self.summrize_trip()

    def set_EV(self):
        for ID in range(self.Num_EV):
            ev = EV(ID,self.TripType,self.ChargeType)
            self.List_EV.append(ev)
    def cal_EVtrip(self):
        
        for ev in self.List_EV:
            evtrip = EVTrip(ev,self.EVDayTrip,self.StartTime,self.EndTime) 
            self.Dict_EVTrip[ev.ID]=evtrip 
    def summrize_trip(self):
        for ev in self.List_EV:        
            for timestep in range(len(self.TripHourRange)):
                dttime = self.TripHourRange[timestep]
                self.NumHomehour[timestep] = 0
                self.NumOfficehour[timestep] = 0
                self.NumOtherhour[timestep] = 0
                self.NumTriphour[timestep] = 0
                self.NumBASEhour[timestep] = 0
                self.EVGroupTriphour[timestep]=0

                for ev in self.List_EV:
                    ID = ev.ID
                    self.EVGroupTriphour[timestep] += self.Dict_EVTrip[ID].EV_Triphour[dttime]*self.TripRatio
                    EV_Place = self.Dict_EVTrip[ID].EV_Placehour[dttime]
                    if EV_Place == "Home":
                        self.NumHomehour[timestep] +=1
                    elif EV_Place == "Office":
                        self.NumOfficehour[timestep] +=1
                    elif EV_Place == "Other":
                        self.NumOtherhour[timestep] +=1
                    else:
                        self.NumTriphour[timestep] +=1
                    if EV_Place == self.Dict_EVTrip[ev.ID].Base:
                        self.NumBASEhour[timestep]+=1

class EVGroupCharge():
    def __init__(self,name,EVGroupTrip,init_energyrate,min_energyrate,ChargeCapacity,BatteryCapacity,TimeRange,Demand,Generation,Is_opt_capacity,Default_solarcapacity = 1):
        
        self.EVGroupTrip = EVGroupTrip
        self.Num_EV = EVGroupTrip.Num_EV
        self.init_energyrate = init_energyrate
        self.min_energyrate = min_energyrate
        self.TripEfficiency = 7 #km/kWh
        self.ChargeEfficiency = 0.9
        self.StartTime = TimeRange[0]
        self.EndTime = TimeRange[-1]
        self.ChargeourRange =  TimeRange
        self.n_range = len(TimeRange)
        self.Output_EVGroupChargehour=np.empty(self.n_range)
        self.opt_EVGroupChargehour=np.empty(self.n_range, dtype=object)
        self.opt_EVGroupDischargehour=np.empty(self.n_range, dtype=object)
        self.ChargeCapacity = ChargeCapacity
        self.EVGroupChargeCapacity = self.Num_EV * self.ChargeCapacity
        self.Output_EVGroupEnergy = np.empty(self.n_range)
        self.opt_EVGroupEnergy = np.empty(self.n_range, dtype=object)
        self.BatteryCapacity = BatteryCapacity
        self.EVGroupBatteryCapacity = self.BatteryCapacity*self.Num_EV
        self.EVGroupEnergy_cur = self.EVGroupBatteryCapacity*self.init_energyrate
        self.Output_EVGroupEnergy=np.empty(self.n_range)
        self.Demand = Demand
        self.cal_Demand_cur=0
        self.Output_cal_BuyPower = np.empty(self.n_range)
        self.EVGroupTripenergy = np.empty(self.n_range)
        self.opt_cal_BuyPower = np.empty(self.n_range, dtype=object)
        self.opt_cal_BuyPowerEnergy = np.empty(self.n_range, dtype=object)
        self.Dict_summary = {}
        self.Dict_summary["name"]=name
        self.Dict_summary["Num_EV"]=EVGroupTrip.Num_EV
        self.Defaultsolarcapacity=Default_solarcapacity
        
        self.cal_BuyPowerEnergy = 0
        self.Generation = Generation
        self.Is_opt_capacity = Is_opt_capacity
        self.set_linearproblem()
        self.set_EVGroupCharge()

    
    def set_linearproblem(self):
        self.model = pulp.LpProblem('linear_programming', pulp.LpMinimize)
        
      
    def set_EVGroupCharge(self):
        #set variables
        self.contractpower      = pulp.LpVariable("contractpower", lowBound = 0, cat = 'continuous')
        self.energycost               = pulp.LpVariable("energycost",          lowBound = 0, cat = 'continuous')
        self.contractcost               = pulp.LpVariable("contractcost",          lowBound = 0, cat = 'continuous')
        self.cost               = pulp.LpVariable("cost",          lowBound = 0, cat = 'continuous')
        self.opt_cal_BuyPowerEnergy = pulp.LpVariable("buypowerenergy", lowBound = 0, cat = 'continuous')
        #objective
        self.model += self.cost

        if self.Is_opt_capacity:
            self.solar_capacity = pulp.LpVariable("solar_capacity",lowBound = 0, cat = 'continuous')
        else:
            self.solar_capacity = self.Defaultsolarcapacity

        
        for ind in range(len(self.ChargeourRange)):
            dttime =datetime.datetime.strptime(self.ChargeourRange[ind],'%Y-%m-%d %H:%M:%S')
            ind_trip = np.where(self.EVGroupTrip.TripHourRange==dttime)[0]
            Trip = self.EVGroupTrip.EVGroupTriphour[ind_trip]
            NumBase = self.EVGroupTrip.NumBASEhour[ind_trip]
            #set charge
            self.opt_EVGroupChargehour[ind]   = pulp.LpVariable("charge_"+str(ind)        ,0,self.ChargeCapacity*NumBase,'continuous')
            self.opt_EVGroupDischargehour[ind]= pulp.LpVariable("discharge_"+str(ind)     ,0,self.ChargeCapacity*NumBase,'continuous')
            self.opt_cal_BuyPower[ind]        = pulp.LpVariable("buypower_"+str(ind)      , lowBound = 0, cat = 'continuous')
            self.opt_EVGroupEnergy[ind]       = pulp.LpVariable("Energy_"+str(ind)        ,self.EVGroupBatteryCapacity*self.min_energyrate,self.EVGroupBatteryCapacity, cat = 'continuous')
        
            #constraints
            self.cal_Demand_cur = self.Demand[ind] + self.opt_EVGroupChargehour[ind] - self.opt_EVGroupDischargehour[ind] - self.solar_capacity*self.Generation[ind]
            self.model += self.cal_Demand_cur <= self.opt_cal_BuyPower[ind]
            self.model += self.contractpower  >= self.opt_cal_BuyPower[ind]
            
            #calculate battery energy
            if ind == 0:
                self.model += self.opt_EVGroupEnergy[ind] == self.EVGroupEnergy_cur + self.opt_EVGroupChargehour[ind]*self.ChargeEfficiency - self.opt_EVGroupDischargehour[ind]*(1/self.ChargeEfficiency)- Trip/self.TripEfficiency
            else:
                self.model += self.opt_EVGroupEnergy[ind] == self.opt_EVGroupEnergy[ind-1] + self.opt_EVGroupChargehour[ind]*self.ChargeEfficiency - self.opt_EVGroupDischargehour[ind]*(1/self.ChargeEfficiency)- Trip/self.TripEfficiency
            self.EVGroupTripenergy[ind] = Trip/self.TripEfficiency/self.ChargeEfficiency

        # declare objective
        self.opt_cal_BuyPowerEnergy = pulp.lpSum(self.opt_cal_BuyPower)
        self.model += self.opt_EVGroupEnergy[-1]>=self.EVGroupBatteryCapacity*self.init_energyrate
        self.model += self.energycost == self.cal_energycost(self.opt_cal_BuyPowerEnergy,self.EVGroupTripenergy.sum())
        self.model += self.contractcost == self.cal_contractycost(self.contractpower)
        self.model += self.cost == self.cal_cost(self.energycost,self.contractcost,self.solar_capacity,self.Num_EV)
        
        self.cal_optimization()
        self.cal_EVGroupCharge()
        self.cal_Demand_cur=self.cal_Demand_cur.value()

    def cal_optimization(self):
        #pulp.LpSolverDefault.msg = 1
        self.results = self.model.solve(pulp.PULP_CBC_CMD(msg = False))
        print(pulp.LpStatus[self.results])

    def cal_energycost(self,ComsumtionEnergy,Trip):
        Price_ComsumptionEnergy = 16 #yen/kWh
        energycost = (ComsumtionEnergy-Trip)*Price_ComsumptionEnergy/(10**4)
        return energycost
    
    def cal_contractycost(self,ContractPower):
        Price_ContaractPower = 1684 #yen/kW/year
        contractcost =  ContractPower * Price_ContaractPower/(10**4)*12
        return contractcost

    def cal_cost(self,energycost,contractcost,SolarCapacity,Num_V2H):
        Price_ini_Solarpanel = 25.5 #10kyen/kW
        lifetime_Solarpanel = 20 #year
        Price_om_Solarpanel = 0.5 #10kyen/kW/year
        
        
        Price_init_V2H = 33 #10kyen
        Price_om_V2H = 0.6 #10kyen
        lifetime_V2H = 10 #year
        

        Cost = energycost+contractcost+SolarCapacity * (Price_ini_Solarpanel/lifetime_Solarpanel+Price_om_Solarpanel)+Num_V2H*(Price_init_V2H/lifetime_V2H+Price_om_V2H)
        
        return(Cost)
    
    


    def cal_EVGroupCharge(self):
        # solve 
        for ind in range(len(self.opt_EVGroupChargehour)):
            #set charge
            dttime =datetime.datetime.strptime(self.ChargeourRange[ind],'%Y-%m-%d %H:%M:%S')
            ind_trip = np.where(self.EVGroupTrip.TripHourRange==dttime)[0]
            TripEnergy = self.EVGroupTrip.EVGroupTriphour[ind_trip]
            self.Output_EVGroupChargehour[ind]=self.opt_EVGroupChargehour[ind].value()-self.opt_EVGroupDischargehour[ind].value()
            self.Output_cal_BuyPower[ind]     =self.opt_cal_BuyPower[ind].value()
            self.Output_EVGroupEnergy[ind]    =self.opt_EVGroupEnergy[ind].value()
        if self.Is_opt_capacity:
            self.solar_capacity=self.solar_capacity.value()
        self.Dict_summary["Demand"]=self.Demand.sum()
        self.Dict_summary["RES"]=self.solar_capacity*self.Generation.sum()
        self.Dict_summary["SolarCapacity"]=self.solar_capacity
        self.Dict_summary["BuyPowerEnergy"]=self.opt_cal_BuyPowerEnergy.value()
        self.Dict_summary["TripEnergy"]=self.EVGroupTripenergy.sum()
        self.Dict_summary["ContractPower"]=self.contractpower.value()
        self.Dict_summary["Cost"]=self.cost.value()
        self.Dict_summary["EnergyCost"]=self.energycost.value()
        self.Dict_summary["ContractCost"]=self.contractcost.value()
        self.Dict_summary["Is_opt_capacity"]=self.Is_opt_capacity
        
        

def extract_timeseriesdata(data,TripHourRange,StartTime,EndTime):
    x = np.fromiter(data.keys(), dtype=object)
    y = np.fromiter(data.values(), dtype=list)

    Index = (TripHourRange >=StartTime)&(TripHourRange < EndTime)
    x_extract = x[Index]
    y_extract = y[Index]
    return x_extract,y_extract

def sample_demand(StartTime,EndTime):
    HourRange =  pd.date_range(start=StartTime,end=EndTime,freq='h')
    Demand = np.random.uniform(0,200,len(HourRange))
    return(Demand)
def dt(Year,month,day):
    return datetime.datetime(Year,month,day)

#%%
if __name__=="__main__":
    d1 = datetime.datetime.now().strftime('%H:%M:%S')
    print(d1,"////DEBUGSTART////")

    ####DEBUG PACKAGE#####
    starttime = dt(2021,1,1)
    endtime = dt(2022,1,1)
    
    ev = EV(1,"Commuter","V2H")
    d2 = datetime.datetime.now().strftime('%H:%M:%S')
    print(d2,"success Create_EV")
    #for i in range(10):
    #    evtrip = EVTrip(ev,starttime,endtime)
    evdaytrip = EVDayTrip("All")
    evtrip = EVTrip(ev,evdaytrip,starttime,endtime)
    d3 = datetime.datetime.now().strftime('%H:%M:%S')
    print(d3,"success EVTrip") 
    evgrouptrip = EVGroupTrip("All",10,"Commuter","V2H",starttime,endtime)
    d4 = datetime.datetime.now().strftime('%H:%M:%S')
    print(d4,"success EVGroupTrip") 
    evgroupcharge = EVGroupCharge("test",evgrouptrip,0.5,0.3,6,62,pd.date_range(start=starttime,end=endtime,freq='h').strftime('%Y-%m-%d %H:%M:%S'),sample_demand(starttime,endtime),sample_demand(starttime,endtime),True)
    d5 = datetime.datetime.now().strftime('%H:%M:%S')
    print(d5,"success EVGroupCharge") 
    



# %%
def cal_TripDistMean():
    df_TripDistMean = pd.read_excel("TripDistMean.xlsx",skiprows=2)
    df_TripDistMean.columns =  ["weekday_code","weekday","cartype_code","cartype","purpose_code","purpose","region_code","region","tripdistmean","comment"]
    idx_tripdistmean =  (df_TripDistMean["weekday_code"]==1)&(df_TripDistMean["cartype_code"]==1)&(df_TripDistMean["region_code"]==100)
    TripDistMean = df_TripDistMean.loc[idx_tripdistmean,"tripdistmean"].values
    return(TripDistMean)

# %%
