#%%
from create_EVmodel3 import EVGroupTrip,EVGroupCharge
from create_SolarPower import get_solarpowerdata
import pandas as pd
import datetime
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


#%%
#Set Input and Output
Num_Vehicle = 15
InputFolder="BuildingDemand_Input"
starttime = datetime.datetime(2012,1,1)
endtime = datetime.datetime(2015,4,1)
OutputFolder = f"EnergyManagement_Output_{Num_Vehicle}"
os.makedirs(OutputFolder,exist_ok=True)
Inst_solarpowerdata = get_solarpowerdata()



#%%
#Set Scinarios
dictScinario={}
Scinario = 1
dictScinario[Scinario]={}
dictScinario[Scinario]["NumEV"]=0
dictScinario[Scinario]["PVw/EV"]=False
dictScinario[Scinario]["NumICE"]=Num_Vehicle
dictScinario[Scinario]["ControlRatio"]=0
dictScinario[Scinario]["Opt_BESS"]=False
dictScinario[Scinario]["PVCapacity_Scinario"]=1
Scinario = 2
dictScinario[Scinario]={}
dictScinario[Scinario]["NumEV"]=0
dictScinario[Scinario]["PVw/EV"]=True
dictScinario[Scinario]["NumICE"]=Num_Vehicle
dictScinario[Scinario]["ControlRatio"]=0
dictScinario[Scinario]["Opt_BESS"]=False
dictScinario[Scinario]["PVCapacity_Scinario"]=1
Scinario = 3
dictScinario[Scinario]={}
dictScinario[Scinario]["NumEV"]=Num_Vehicle
dictScinario[Scinario]["PVw/EV"]=False
dictScinario[Scinario]["NumICE"]=0
dictScinario[Scinario]["ControlRatio"]=0
dictScinario[Scinario]["Opt_BESS"]=False
dictScinario[Scinario]["PVCapacity_Scinario"]=2
Scinario = 4
dictScinario[Scinario]={}
dictScinario[Scinario]["NumEV"]=Num_Vehicle
dictScinario[Scinario]["PVw/EV"]=False
dictScinario[Scinario]["NumICE"]=0
dictScinario[Scinario]["ControlRatio"]=0
dictScinario[Scinario]["Opt_BESS"]=False
dictScinario[Scinario]["PVCapacity_Scinario"]=2
Scinario = 5
dictScinario[Scinario]={}
dictScinario[Scinario]["NumEV"]=Num_Vehicle
dictScinario[Scinario]["PVw/EV"]=False
dictScinario[Scinario]["NumICE"]=0
dictScinario[Scinario]["ControlRatio"]=1
dictScinario[Scinario]["Opt_BESS"]=False
dictScinario[Scinario]["PVCapacity_Scinario"]=2
Scinario = 6
dictScinario[Scinario]={}
dictScinario[Scinario]["NumEV"]=Num_Vehicle
dictScinario[Scinario]["PVw/EV"]=True
dictScinario[Scinario]["NumICE"]=0
dictScinario[Scinario]["ControlRatio"]=1
dictScinario[Scinario]["Opt_BESS"]=False
dictScinario[Scinario]["PVCapacity_Scinario"]=5
# Scinario = 7
# dictScinario[Scinario]={}
# dictScinario[Scinario]["NumEV"]=0
# dictScinario[Scinario]["PVw/EV"]=False
# dictScinario[Scinario]["NumICE"]=10
# dictScinario[Scinario]["ControlRatio"]=0
# dictScinario[Scinario]["Opt_BESS"]=True
# dictScinario[Scinario]["PVCapacity_Scinario"]=2
# Scinario = 8
# dictScinario[Scinario]={}
# dictScinario[Scinario]["NumEV"]=0
# dictScinario[Scinario]["PVw/EV"]=True
# dictScinario[Scinario]["NumICE"]=10
# dictScinario[Scinario]["ControlRatio"]=0
# dictScinario[Scinario]["Opt_BESS"]=True
# dictScinario[Scinario]["PVCapacity_Scinario"]=7
#%%
#Input Demand list
Cluster = pd.read_csv("cluster.csv")
Cluster.columns = ["name","cluster"]

for i in range(1):#%%
    #Set initial solar capacity
    SolarCapacity={}
    for name in Cluster["name"].values:
        SolarCapacity[name]={}
        SolarCapacity[name][1]=0

    #%%
    #Set EV trip
    EVgrouptrip = {}
    TripType="Office"
    for Num_EV in [0,Num_Vehicle]:
        EVgrouptrip[Num_EV]=EVGroupTrip("All",Num_EV,starttime,endtime,False,TripType,10000)

    #%%
    List_summary = []

    for file in os.listdir(InputFolder)[:]:
        name = file.split(".")[0]
        if name not in Cluster["name"].values:continue
        EV_summary = []
        for scinario in dictScinario:
            Num_EV = dictScinario[scinario]["NumEV"]
            Is_SolarCapacity = dictScinario[scinario]["PVw/EV"]
            ControlRatio = dictScinario[scinario]["ControlRatio"]
            Is_BESScal = dictScinario[scinario]["Opt_BESS"]
            PVCapacity_Scinario = dictScinario[scinario]["PVCapacity_Scinario"]
            Ref_PVCapacity = SolarCapacity[name][PVCapacity_Scinario]
            OutputFile = OutputFolder+"/"+name+"_"+str(scinario)+".csv"
            #if os.path.isfile(OutputFile):continue
            print(name,scinario)
            DF = pd.read_csv(InputFolder+"/"+file,index_col=0)
            DF = DF.dropna(axis=0)
            DF.loc[DF["Demand_Power"]<0,"Demand_Power"]=0
            Evgroupcharge = EVGroupCharge(name,EVgrouptrip[Num_EV],"V2B",0.5,0.3,6,62,DF.index.to_numpy(),DF["Demand_Power"].to_numpy(),DF["RE_Power"].to_numpy(),Is_SolarCapacity,Ref_PVCapacity,ControlRatio,Is_BESScal)
            if Evgroupcharge.results==None:break
            DF["EV_Charge"]=Evgroupcharge.Output_EVGroupChargehour[TripType][bool(np.random.binomial(1,ControlRatio))]
            DF["EV_Energy"]=Evgroupcharge.Output_EVGroupEnergy[TripType][bool(np.random.binomial(1,ControlRatio))][:-1]
            DF["BESS_Charge"]=Evgroupcharge.BESS_Charge - Evgroupcharge.BESS_Discharge
            DF["BESS_Energy"]=Evgroupcharge.BESS_Energy[:-1]
            DF["BuyPower"]=Evgroupcharge.Output_cal_BuyPower
            DF["RE_Power"]=Evgroupcharge.Generation*Evgroupcharge.solar_capacity
            DF["Trip"]=Evgroupcharge.EVGroupTripenergy[TripType][bool(np.random.binomial(1,ControlRatio))]
            DF.to_csv(OutputFile)
            Evgroupcharge.Dict_summary["Scinario"]=scinario
            #print(Evgroupcharge.Dict_summary["RES"],DF["RE_Power"].sum(),Evgroupcharge.solar_capacity)
            EV_summary.append(Evgroupcharge.Dict_summary)
            SolarCapacity[name][scinario] = Evgroupcharge.solar_capacity
        if Evgroupcharge.results==None:continue
        List_summary=List_summary+EV_summary

    #%%
    #Output
    DF_summary = pd.DataFrame(List_summary)
    print(DF_summary)
    DF_summary.to_csv(f"Summary_EV{Num_Vehicle}_{i}.csv",index=False)

#%%



# %%


