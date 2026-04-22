#%%
import os
import pandas as pd
import numpy as np
import datetime
import random
from time import time
import pulp
import matplotlib.pyplot as plt
import cvxpy as cp
random.seed(314)

#%%
class EV():
    def __init__(self,ID,TripType):
        self.ID = ID
        self.TripType = TripType
        

class EVDayTrip():
    def __init__(self,Region):
        self.Region = Region
        self.Dict_RegionCode={}
        self.Dict_RegionCode["All"]=100
        self.Dict_RegionCode["Hokkaido"]=1
        self.Dict_RegionCode["Kitatohoku"]=2
        self.Dict_RegionCode["Minamitohoku"]=3
        self.Dict_RegionCode["Kantonairiku"]=4
        self.Dict_RegionCode["Kantorinkai"]=5
        self.Dict_RegionCode["Tokai"]=6
        self.Dict_RegionCode["Hokuriku"]=7
        self.Dict_RegionCode["Kinkinairiku"]=8
        self.Dict_RegionCode["Kinkirinkai"]=9
        self.Dict_RegionCode["Sanin"]=10
        self.Dict_RegionCode["Sanyo"]=11
        self.Dict_RegionCode["Shikoku"]=12
        self.Dict_RegionCode["Kitakyusyu"]=13
        self.Dict_RegionCode["Minamikyusyu"]=14
        self.Dict_RegionCode["Okinawa"]=15
        self.Region_code = self.Dict_RegionCode[self.Region]

        self.make_DayTrip()
        self.analyze_UserTypeRatio()

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
        Dict_Tripcount = self.make_tripcount(self.Region_code)
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
    def __init__(self,EV,EVDayTrip,StartTime,EndTime,Is_TripRatiobyRegion,TripType):
        self.EV =EV
        self.EV_TripDay = {}
        self.StartTime = StartTime
        self.EndTime =  EndTime
        self.TripDayRange = pd.date_range(start=self.StartTime,end=self.EndTime,freq='d')
        self.TRIPSPEED = 34 #km/h
        self.EVDayTrip = EVDayTrip

        self.Dict_RegionCode={}
        self.Dict_RegionCode["All"]=100
        self.Dict_RegionCode["Hokkaido"]=1
        self.Dict_RegionCode["Kitatohoku"]=2
        self.Dict_RegionCode["Minamitohoku"]=3
        self.Dict_RegionCode["Kantonairiku"]=4
        self.Dict_RegionCode["Kantorinkai"]=5
        self.Dict_RegionCode["Tokai"]=6
        self.Dict_RegionCode["Hokuriku"]=7
        self.Dict_RegionCode["Kinkinairiku"]=8
        self.Dict_RegionCode["Kinkirinkai"]=9
        self.Dict_RegionCode["Sanin"]=10
        self.Dict_RegionCode["Sanyo"]=11
        self.Dict_RegionCode["Shikoku"]=12
        self.Dict_RegionCode["Kitakyusyu"]=13
        self.Dict_RegionCode["Minamikyusyu"]=14
        self.Dict_RegionCode["Okinawa"]=15
        self.Region = self.EVDayTrip.Region
        self.Region_code = self.Dict_RegionCode[self.Region]

        
        self.TripRatio = self.cal_TripRate(self.Region_code)
        

        #個別EVログ
        self.EV_Triphour={}
        self.EV_TripDay={}
        self.EV_Placehour={}
        self.EV_Energy={}   

        Dict_Base = {}
        Dict_Base["Commuter"]="Home"
        Dict_Base["Private"]="Home"
        Dict_Base["Office"]="Office"
        Dict_Base["Service"]="Office"
        if not Is_TripRatiobyRegion:
            self.EV.TripType = TripType
        else:
            UserType = list(self.EVDayTrip.Dict_UserTypeRatio.keys())
            UserTypeRatio = list(self.EVDayTrip.Dict_UserTypeRatio.values())
            self.EV.TripType = random.choices(UserType, k = 1, weights =UserTypeRatio )[0]
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
    def __init__(self,Region,
                 Num_EV,
                 StartTime,
                 EndTime,
                 Is_TripRatiobyRegion,
                 TripType,
                 Annual_TripDistance,):
        self.Region = Region
        self.Num_EV = Num_EV
        self.StartTime = StartTime
        self.EndTime = EndTime
        self.List_EV=[]
        self.Dict_EVTrip={}
        self.TripHourRange =  pd.date_range(start=self.StartTime,end=self.EndTime,freq='h')
        self.n_range=len(self.TripHourRange)
        self.Annual_TripDistance = Annual_TripDistance
        
        self.Model_TripDistance = 1
        self.TripDistanceRatio = self.Annual_TripDistance/self.Model_TripDistance
        self.EVGroupTriphour={}
        self.NumHomehour={}
        self.NumOfficehour={}
        self.NumTriphour={}
        self.NumGroupEV = {}
        List_UserType=["Commuter","Office","Private","Service"]
        for UserType in List_UserType:
            self.EVGroupTriphour[UserType]={}
            self.NumHomehour[UserType]={}
            self.NumOfficehour[UserType]={}
            self.NumTriphour[UserType]={}
            self.NumGroupEV[UserType]={}
            for Control in [True,False]:
                self.EVGroupTriphour[UserType][Control]=np.zeros(self.n_range)
                self.NumHomehour[UserType][Control] = np.zeros(self.n_range)
                self.NumOfficehour[UserType][Control] = np.zeros(self.n_range)
                self.NumTriphour[UserType][Control] = np.zeros(self.n_range)
                self.NumGroupEV[UserType][Control]=0
        self.Is_TripRatiobyRegion = Is_TripRatiobyRegion
        self.set_Scaleratio(self.Num_EV)
        self.TripType = TripType
        #print(TripType)
        self.set_EV()
        self.EVDayTrip = EVDayTrip(Region)
        self.cal_EVtrip()
        self.summrize_trip()
    def set_Scaleratio(self,Num_EV):
        if Num_EV < 100:
            self.Scale_Num_EV = Num_EV
            self.Scale = 1
        else:
            self.Scale_Num_EV = 100
            self.Scale = int(Num_EV/100)

    def set_EV(self):
        for ID in range(self.Scale_Num_EV):
            ev = EV(ID,self.TripType)
            self.List_EV.append(ev)
    def cal_EVtrip(self):
        
        for ev in self.List_EV:
            evtrip = EVTrip(ev,self.EVDayTrip,self.StartTime,self.EndTime,self.Is_TripRatiobyRegion,self.TripType) 
            self.Dict_EVTrip[ev.ID]=evtrip 
            TripType= self.Dict_EVTrip[ev.ID].EV.TripType
            for Control in [True,False]:
                self.NumGroupEV[TripType][Control]+=self.Scale
    def summrize_trip(self):      
        for timestep in range(len(self.TripHourRange)):
            dttime = self.TripHourRange[timestep]

            for ev in self.List_EV:
                ID = ev.ID
                TripType= self.Dict_EVTrip[ev.ID].EV.TripType
                #Control = bool(np.random.binomial(1,self.ControlRatio))
                
                for Control in [True,False]:
                    self.EVGroupTriphour[TripType][Control][timestep] += self.Dict_EVTrip[ID].EV_Triphour[dttime]*self.TripDistanceRatio*self.Scale
                    EV_Place = self.Dict_EVTrip[ID].EV_Placehour[dttime]
                    if EV_Place == "Home":
                        self.NumHomehour[TripType][Control][timestep] +=self.Scale
                    elif EV_Place == "Office":
                        self.NumOfficehour[TripType][Control][timestep] +=self.Scale
                    elif EV_Place == "Other":
                        pass
                    else:
                        self.NumTriphour[TripType][Control][timestep]+=self.Scale
               

class EVGroupCharge():
    def __init__(self,name,EVGroupTrip,ChargeType,init_energyrate,min_energyrate,ChargeCapacity,BatteryCapacity,TimeRange,Demand,Generation,Is_opt_capacity,Default_solarcapacity = 1,ControlRatio=1):
        
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
        self.ChargeCapacity = ChargeCapacity
        self.EVGroupChargeCapacity = self.Num_EV * self.ChargeCapacity
        
        self.ChargeType = ChargeType
        
        self.BatteryCapacity = BatteryCapacity
        self.ControlRatio = ControlRatio

        
        self.Demand = Demand
        self.Output_cal_BuyPower = np.empty(self.n_range)
        
        self.Dict_summary = {}
        self.Dict_summary["name"]=name
        self.Dict_summary["Num_EV"]=EVGroupTrip.Num_EV
        self.Defaultsolarcapacity=Default_solarcapacity
        self.opt_EVGroupChargehour={}
        self.opt_EVGroupDischargehour={}
        self.opt_EVGroupEnergy={}
        self.nonopt_EVGroupChargehour={}
        self.nonopt_EVGroupEnergy={}
        self.EVGroupBatteryCapacity={}
        self.EVGroupEnergy_cur={}
        self.EVGroupTripenergy={}
        self.Output_EVGroupChargehour={}
        self.Output_EVGroupEnergy={}
        self.constraints=[]
        self.cost=cp.Variable((1,),name="cost")
        self.energycost=cp.Variable((1,),name="energycost")
        self.contractcost=cp.Variable((1,),name="contractcost")

        



        #self.List_UserType=["Commuter","Office","Private","Service"]
        if self.EVGroupTrip.Is_TripRatiobyRegion==True:
            self.List_UserType=["Commuter","Office","Private"]
        else:
            self.List_UserType=[self.EVGroupTrip.TripType]
        for UserType in self.List_UserType:
            self.opt_EVGroupChargehour[UserType]={}
            self.opt_EVGroupDischargehour[UserType]={}
            self.opt_EVGroupEnergy[UserType]={}
            self.nonopt_EVGroupChargehour[UserType]={}
            self.nonopt_EVGroupEnergy[UserType]={}
            self.EVGroupBatteryCapacity[UserType]={}
            self.EVGroupEnergy_cur[UserType]={}
            self.EVGroupTripenergy[UserType]={}
            self.Output_EVGroupChargehour[UserType]={}
            self.Output_EVGroupEnergy[UserType]={}
            for Control in [True, False]:
                self.EVGroupBatteryCapacity[UserType][Control] = self.BatteryCapacity*self.EVGroupTrip.NumGroupEV[UserType][Control]
                self.EVGroupEnergy_cur[UserType][Control] = self.EVGroupBatteryCapacity[UserType][Control]*self.init_energyrate
                if Control==True:
                    self.opt_EVGroupChargehour[UserType][Control]   = cp.Variable((self.n_range,),name="Charge_"+UserType)
                    self.opt_EVGroupDischargehour[UserType][Control]= cp.Variable((self.n_range,),name="Discharge_"+UserType)
                    self.opt_EVGroupEnergy[UserType][Control]       = cp.Variable((self.n_range,),name="Energy_"+UserType)
                    self.constraints.append(self.opt_EVGroupChargehour[UserType][Control]>=0)
                    self.constraints.append(self.opt_EVGroupDischargehour[UserType][Control]>=0)
                    self.constraints.append(self.opt_EVGroupEnergy[UserType][Control]>=self.EVGroupBatteryCapacity[UserType][Control]*self.min_energyrate)
                    self.constraints.append(self.opt_EVGroupEnergy[UserType][Control]<=self.EVGroupBatteryCapacity[UserType][Control])
                else:
                    self.nonopt_EVGroupChargehour[UserType][Control]=np.zeros(self.n_range)
                    self.nonopt_EVGroupEnergy[UserType][Control] = np.zeros(self.n_range)
                self.EVGroupTripenergy[UserType][Control] = np.zeros(self.n_range)
                self.Output_EVGroupChargehour[UserType][Control] =np.empty(self.n_range)
                self.Output_EVGroupEnergy[UserType][Control]  = np.empty(self.n_range)
        
        
        
        self.cal_BuyPowerEnergy = 0
        self.Generation = Generation
        self.Is_opt_capacity = Is_opt_capacity
        self.set_EVGroupCharge()
        self.solve_linearproblem(self.cost,self.constraints)
        self.cal_EVGroupCharge()
        

    
    def solve_linearproblem(self,cost,constraints):
        self.model = cp.Problem(cp.Minimize(cost), constraints)
        #print(cp.installed_solvers() )
        self.results = self.model.solve(verbose=False,solver="SCIPY")
        print(self.model.status)
        #for variable in self.model.variables():
        #    print("Variable %s: value %s" % (variable.name(), variable.value))
        
      
    def set_EVGroupCharge(self):
        #set variables
        self.contractpower      = cp.Variable((1,),name="contractpower")
        self.opt_cal_BuyPowerEnergy = cp.Variable((1,),name="BuyPowerEnergy")
        self.constraints.append(self.contractpower>=0)
        self.constraints.append(self.opt_cal_BuyPowerEnergy>=0)
        

        if self.Is_opt_capacity:
            self.solar_capacity = cp.Variable((1,),name="solarcapacity")
            self.constraints.append(self.solar_capacity>=0)
        else:
            self.solar_capacity = self.Defaultsolarcapacity
    
        self.opt_cal_BuyPower = cp.Variable((self.n_range,),name="Buypower")
        self.constraints.append(self.opt_cal_BuyPower>=0)
        
        #for ind in range(len(self.ChargeourRange)):
        dttime =[datetime.datetime.strptime(ind,'%Y-%m-%d %H:%M:%S') for ind in self.ChargeourRange]
        ind_trip = [np.where(self.EVGroupTrip.TripHourRange==dt)[0][0] for dt in dttime]
        
        self.Demand_cur = self.Demand- self.solar_capacity*self.Generation
        for UserType in self.List_UserType:
            
            #for Control in [True,False]:
            Control = bool(np.random.binomial(1,self.ControlRatio))
            
            trip = self.EVGroupTrip.EVGroupTriphour[UserType][Control][ind_trip]
            self.EVGroupTripenergy[UserType][Control]= trip/self.TripEfficiency/self.ChargeEfficiency

            self.Cond_Commuter_V2H =  (UserType=="Commuter")&(self.ChargeType == "V2H")
            self.Cond_Private_V2H =  (UserType=="Private")&(self.ChargeType == "V2H")
            self.Cond_Commuter_V2B =  (UserType=="Commuter")&(self.ChargeType == "V2B")
            self.Cond_Office_V2B =  (UserType=="Office")&(self.ChargeType == "V2B")
            
            self.Cond_Commuter_V2G =  (UserType=="Commuter")&(self.ChargeType == "V2G")
            self.Cond_Private_V2G =  (UserType=="Private")&(self.ChargeType == "V2G")
            self.Cond_Office_V2G =  (UserType=="Office")&(self.ChargeType == "V2G")

            if Control==True:
                if (self.Cond_Commuter_V2H|self.Cond_Private_V2H):
                    NumBase = self.EVGroupTrip.NumHomehour[UserType][Control][ind_trip]
                if (self.Cond_Commuter_V2B|self.Cond_Office_V2B):
                    NumBase = self.EVGroupTrip.NumOfficehour[UserType][Control][ind_trip]  
                if (self.Cond_Commuter_V2G|self.Cond_Private_V2G|self.Cond_Office_V2G):
                    NumBase = self.EVGroupTrip.NumHomehour[UserType][Control][ind_trip]+self.EVGroupTrip.NumOfficehour[UserType][Control][ind_trip]
                self.constraints.append(self.opt_EVGroupChargehour[UserType][Control]<=self.ChargeCapacity*NumBase)
                self.constraints.append(self.opt_EVGroupDischargehour[UserType][Control]<=self.ChargeCapacity*NumBase)
                self.constraints.append(self.opt_EVGroupEnergy[UserType][Control][0] == self.EVGroupEnergy_cur[UserType][Control])
                self.constraints.append(self.opt_EVGroupEnergy[UserType][Control][1:] == self.opt_EVGroupEnergy[UserType][Control][:-1] + self.opt_EVGroupChargehour[UserType][Control][:-1]*self.ChargeEfficiency - self.opt_EVGroupDischargehour[UserType][Control][:-1]*(1/self.ChargeEfficiency)- trip[:-1]/self.TripEfficiency)
                self.constraints.append(self.opt_EVGroupEnergy[UserType][Control][-1] == self.EVGroupBatteryCapacity[UserType][Control])
                self.Demand_cur =  self.Demand_cur + self.opt_EVGroupChargehour[UserType][Control] - self.opt_EVGroupDischargehour[UserType][Control]
                
                
            else:
                if (UserType=="Commuter")|(UserType=="Private"):
                    NumBase = self.EVGroupTrip.NumHomehour[UserType][Control][ind_trip]
                else:
                    NumBase = self.EVGroupTrip.NumOfficehour[UserType][Control][ind_trip]
                self.nonopt_EVGroupEnergy[UserType][Control][0]       = self.EVGroupEnergy_cur[UserType][Control]
                    
                for ind in range(1,len(NumBase)):
                    ChargeblePower = self.EVGroupBatteryCapacity[UserType][Control] - self.nonopt_EVGroupEnergy[UserType][Control][ind-1]
                    self.nonopt_EVGroupChargehour[UserType][Control][ind-1]  = np.minimum(self.ChargeCapacity*NumBase[ind-1],ChargeblePower*(1/self.ChargeEfficiency))
                    self.nonopt_EVGroupEnergy[UserType][Control][ind]       = self.nonopt_EVGroupEnergy[UserType][Control][ind-1]+self.nonopt_EVGroupChargehour[UserType][Control][ind-1]*self.ChargeEfficiency- trip[ind-1]/self.TripEfficiency
                self.Demand_cur =  self.Demand_cur + self.nonopt_EVGroupChargehour[UserType][Control]
            self.constraints.append(self.opt_cal_BuyPower  >= self.Demand_cur)  
            self.constraints.append(self.contractpower  >= self.opt_cal_BuyPower)
        if Control==True:
            Num_V2H = self.Num_EV
            Num_NC = 0
        else:
            Num_V2H = 0
            Num_NC = self.Num_EV

        # declare objective
        self.constraints.append(self.opt_cal_BuyPowerEnergy == cp.sum(self.opt_cal_BuyPower))
        self.constraints.append(self.energycost == self.cal_energycost(self.opt_cal_BuyPowerEnergy,self.EVGroupTripenergy[UserType][Control].sum()))
        self.constraints.append(self.contractcost == self.cal_contractcost(self.contractpower))
        self.constraints.append(self.cost == self.cal_cost(self.energycost,self.contractcost,self.solar_capacity,Num_V2H,Num_NC))
        

    def cal_energycost(self,ComsumtionEnergy,Trip):
        Price_ComsumptionEnergy = 16 #yen/kWh
        energycost = ComsumtionEnergy*Price_ComsumptionEnergy/(10**4)
        return energycost
    
    def cal_contractcost(self,ContractPower):
        Price_ContaractPower = 1684 #yen/kW/year
        contractcost =  ContractPower * Price_ContaractPower/(10**4)*12
        return contractcost

    def cal_cost(self,energycost,contractcost,SolarCapacity,Num_V2H,Num_NC):
        Price_ini_Solarpanel = 25.5 #10kyen/kW
        lifetime_Solarpanel = 20 #year
        Price_om_Solarpanel = 0.5 #10kyen/kW/year
        
        
        Price_init_V2H = 33 #10kyen
        Price_om_V2H = 0.6 #10kyen
        lifetime_V2H = 10 #year

        Price_init_NC = 15 #10kyen
        Price_om_NC = 0.1 #10kyen
        lifetime_NC = 10 #year



        

        Cost = energycost+contractcost+SolarCapacity * (Price_ini_Solarpanel/lifetime_Solarpanel+Price_om_Solarpanel)+Num_V2H*(Price_init_V2H/lifetime_V2H+Price_om_V2H)+Num_NC*(Price_init_NC/lifetime_NC+Price_om_NC)
        
        return(Cost)


    def cal_EVGroupCharge(self):
        # solve 
        self.Dict_summary["TripEnergy"]=0
        for UserType in self.List_UserType:
            #for Control in [True,False]:
            Control = bool(np.random.binomial(1,self.ControlRatio))
            if Control==True:
                self.Output_EVGroupChargehour[UserType][Control]=self.opt_EVGroupChargehour[UserType][Control].value-self.opt_EVGroupDischargehour[UserType][Control].value
                self.Output_EVGroupEnergy[UserType][Control]    =self.opt_EVGroupEnergy[UserType][Control].value
            else:
                self.Output_EVGroupChargehour[UserType][Control]=self.nonopt_EVGroupChargehour[UserType][Control]
                self.Output_EVGroupEnergy[UserType][Control]    =self.nonopt_EVGroupEnergy[UserType][Control]
                
            self.Dict_summary["TripEnergy"]+=self.EVGroupTripenergy[UserType][Control].sum()
        self.Output_cal_BuyPower     =self.opt_cal_BuyPower.value
        
        if self.Is_opt_capacity:
            self.solar_capacity=self.solar_capacity.value[0]
        self.Dict_summary["Demand"]=self.Demand.sum()
        self.Dict_summary["RES"]=self.solar_capacity*self.Generation.sum()
        self.Dict_summary["SolarCapacity"]=self.solar_capacity
        self.Dict_summary["BuyPowerEnergy"]=self.opt_cal_BuyPowerEnergy.value[0]
        self.Dict_summary["ContractPower"]=self.contractpower.value[0]
        self.Dict_summary["Cost"]=self.cost.value[0]
        self.Dict_summary["EnergyCost"]=self.energycost.value[0]
        self.Dict_summary["ContractCost"]=self.contractcost.value[0]
        self.Dict_summary["Is_opt_capacity"]=self.Is_opt_capacity
        self.Dict_summary["TripType"]=self.EVGroupTrip.TripType
        self.Dict_summary["ChargeType"]=self.ChargeType
        self.Dict_summary["ControlRatio"]=self.ControlRatio
        
        

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
    
    ev = EV(1,"Commuter")
    d2 = datetime.datetime.now().strftime('%H:%M:%S')
    print(d2,"success Create_EV")
    #for i in range(10):
    #    evtrip = EVTrip(ev,starttime,endtime)
    evdaytrip = EVDayTrip("All")
    Is_TripRatiobyRegion=True
    TripType = "Commuter"
    evtrip = EVTrip(ev,evdaytrip,starttime,endtime,Is_TripRatiobyRegion,TripType)
    d3 = datetime.datetime.now().strftime('%H:%M:%S')
    print(d3,"success EVTrip") 
    evgrouptrip = EVGroupTrip("All",100,starttime,endtime,Is_TripRatiobyRegion,TripType,1,0.3)
    d4 = datetime.datetime.now().strftime('%H:%M:%S')
    print(d4,"success EVGroupTrip") 
    demand = sample_demand(starttime,endtime)
    solar = sample_demand(starttime,endtime)
    evgroupcharge = EVGroupCharge("test",evgrouptrip,"V2H",0.5,0.3,6,62,pd.date_range(start=starttime,end=endtime,freq='h').strftime('%Y-%m-%d %H:%M:%S'),demand,solar,True)
    d5 = datetime.datetime.now().strftime('%H:%M:%S')
    print(d5,"success EVGroupCharge") 
    List_UserType=["Commuter","Office","Private"]
    List_Charge=[]
    List_Energy = []
    List_Trip = []
    for UserType in List_UserType:
        Charge = pd.DataFrame(evgroupcharge.Output_EVGroupChargehour[UserType])
        Energy = pd.DataFrame(evgroupcharge.Output_EVGroupEnergy[UserType])
        Trip = pd.DataFrame(evgroupcharge.EVGroupTripenergy[UserType])
        List_Charge.append(Charge)
        List_Energy.append(Energy)
        List_Trip.append(Trip)
    ChargeAll = pd.concat(List_Charge,axis=1)
    EnergyAll = pd.concat(List_Energy,axis=1)
    TripAll = pd.concat(List_Trip,axis=1)

    
    

    print(ChargeAll.head(50))
    print(EnergyAll.head(50))
    print(TripAll.head(50))

    print(demand[:50])
    print(solar[:50])
    



# %%
def cal_TripDistMean():
    df_TripDistMean = pd.read_excel("TripDistMean.xlsx",skiprows=2)
    df_TripDistMean.columns =  ["weekday_code","weekday","cartype_code","cartype","purpose_code","purpose","region_code","region","tripdistmean","comment"]
    idx_tripdistmean =  (df_TripDistMean["weekday_code"]==1)&(df_TripDistMean["cartype_code"]==1)&(df_TripDistMean["region_code"]==100)
    TripDistMean = df_TripDistMean.loc[idx_tripdistmean,"tripdistmean"].values
    return(TripDistMean)

# %%
