#%%
import pandas as pd
import numpy as np
from tslearn.metrics import dtw
import matplotlib.pyplot as plt
from tslearn.clustering import TimeSeriesKMeans
from tslearn.preprocessing import TimeSeriesScalerMeanVariance
import os
import datetime
import seaborn as sns
from kneed import KneeLocator
from scipy.spatial.distance import cdist
#%%
def remove_year(DF,datetime_idx,Month):
    DF.index = pd.date_range(start = "2014/"+str(Month).zfill(2)+"/01",periods=24*7,freq="h")
    return (DF)

def extract_1week(DF,datetime_idx,Month,Weekday=1):
    bool_month = datetime_idx.month == Month
    bool_weekday = datetime_idx.weekday == 1
    firsttime = datetime_idx[bool_month&bool_weekday][0]
    idx_firsttime = datetime_idx.get_loc(firsttime)
    datetime1week_idx = datetime_idx[idx_firsttime:idx_firsttime+24*7]
    df = DF.loc[datetime1week_idx,:]
    df = remove_year(df,datetime1week_idx,Month)

    return(df)


#%%
InputFolder="BuildingDemand_Input"
List_Demand = []
List_partDemand = []
List_week = []
error = []
DF_Demand = pd.DataFrame()
data_range = pd.date_range(start=datetime.datetime(2012,1,1),end=datetime.datetime(2016,1,1),freq="h")
DF_Datacount = pd.DataFrame(index=data_range,data=[0]*len(data_range))
for file in os.listdir(InputFolder)[:]:
    name = file.split(".")[0]
    print(name)
    DF = pd.read_csv(InputFolder+"/"+file,index_col=0)
    DF.index= pd.to_datetime(DF.index,format = "%Y-%m-%d %H:%M:%S")
    datetime_idx = DF.index
    if DF["Demand_Power"].max()>DF["Demand_Power"].mean()*5:
        print("error",DF["Demand_Power"].max(),DF["Demand_Power"].mean())
        continue
    sumDemand = DF["Demand_Power"].sum()/1000
    DemandClass=(sumDemand/100).astype(int)*100
    if DemandClass>=1000:continue
    DF["Demand_Power"]=DF["Demand_Power"].ffill()
    DF["Demand_Power"]=DF["Demand_Power"].bfill()
    # # クオーターを計算 (1月-3月がQ1, 4月-6月がQ2, 7月-9月がQ3, 10月-12月がQ4)
    # DF["quarter"] = ((DF.index.month - 1) // 3) + 1

    # # 平日（土日を除外）と土日のインデックスを分ける
    # DF["weekend"] = DF.index.weekday >= 5  # 土日: True, 平日: False

    # # クオーターごとのtime_indexを作成 (1時間ごとに)
    # DF["time_index"] = ((DF.index.month - 1) // 3) * 24 * 3 + DF.index.hour  # クオーター単位、1時間ごと

    # # 平日・土日ごとの時間インデックスを区別 (土日用に調整)
    # DF["time_index"] = DF["time_index"] + (DF["weekend"] * 100000)  # 土日と平日を区別

    #DF["time_index"] =  ((DF.index.month - 1) // 3)*168+DF.index.weekday*24+DF.index.hour
    DF["time_index"] = DF.index.weekday*24+DF.index.hour
    DF["normalized"]=DF["Demand_Power"]/DF["Demand_Power"].max()
    DF_week = DF.groupby("time_index").mean()["normalized"]
    DF_week.name=name
    List_week.append(DF_week)


    DF_Datacount.loc[datetime_idx[0],:]+=1
    DF_Datacount.loc[datetime_idx[-1],:]+=1
    #if datetime_idx[0]<=datetime.datetime(2013,12,1):continue
    #if datetime_idx[-1]>datetime.datetime(2014,12,1):continue
    List_Series = []
    for month in [6,12]:
        DF_e = extract_1week(DF.div(DF.max(),axis=1),datetime_idx,month)
        DF_e = DF_e.sort_index()
        DF_e = DF_e.loc[~DF_e.index.duplicated(),:]["Demand_Power"]
        List_Series.append(DF_e)
    List_partDemand.append(pd.concat(List_Series))
    DF = DF.loc[~DF.index.duplicated(),:]["Demand_Power"].reset_index(drop=True)
    DF.name = name
    List_Demand.append(DF)
#%%
DF_Demand = pd.concat(List_week,axis=1)
DF_Demand = DF_Demand.ffill()
DF_Demand = DF_Demand.bfill().T

print(DF_Demand)



# %%
nm_demanddata = DF_Demand.div(DF_Demand.max(axis=1),axis=0).values
#nm_demanddata = np.sort(nm_demanddata,axis=1)[:,::-1]
N = len(nm_demanddata[0])



#%%
fig, ax = plt.subplots(figsize=(10, 5))
distoritions = []
for i in range(1,11):
    print(i)
    ts_km = TimeSeriesKMeans(n_clusters=i,metric="euclidean",random_state=42,verbose=True)
    ts_km.fit(nm_demanddata)
    distoritions.append(ts_km.inertia_)

ax.plot(range(1,11),distoritions,marker="o",c="k")
ax.set_xticks(range(1,11))
ax.set_xlabel("Number of clusters")
ax.set_ylabel("Within-cluster sum of squares (WSS)")
plt.savefig("IMG/elbow.png")
plt.show()

kneedle = KneeLocator(range(1,11),distoritions,curve="convex",direction="decreasing")
optinal_k = kneedle.knee
print("number of clusters",optinal_k)

#%%
# k-meansクラスタリングの実行
n_clusters = 4
km = TimeSeriesKMeans(n_clusters=n_clusters, metric="euclidean", verbose=True, random_state=42)
y_pred = km.fit_predict(nm_demanddata)

cluster_variances = []


for cluster_id in range(n_clusters):
    cluster_members = nm_demanddata[km.labels_ == cluster_id]
    centroid = km.cluster_centers_[cluster_id].ravel() 
    distances = [np.linalg.norm(ts - centroid) for ts in cluster_members]

    cluster_variances.append({
        "cluster": ["A", "B", "C", "D","E","F"][cluster_id],
        "mean_distance": np.mean(distances),
        "std_distance": np.std(distances),
        "max_distance": np.max(distances),
        "n_samples": len(cluster_members)
    })

df_variances = pd.DataFrame(cluster_variances)
print(df_variances)

# センチロイドの取得
centroids = km.cluster_centers_.reshape(n_clusters, -1)  # shape: (n_clusters, 168)

# 距離行列を計算（ユークリッド距離）
inter_cluster_distances = cdist(centroids, centroids, metric='euclidean')

# クラスタ名のラベル（例: A, B, C, D）
cluster_labels = ["A", "B", "C","D"]

# 距離行列をDataFrameとして表示
distance_df = pd.DataFrame(inter_cluster_distances, index=cluster_labels, columns=cluster_labels)
print(distance_df)

#%%
import copy
y_pred_num = copy.copy(y_pred)
y_pred += 1
y_pred = y_pred.astype(object)
y_pred[y_pred == 1] = "A"
y_pred[y_pred == 2] = "B"
y_pred[y_pred == 3] = "C"
y_pred[y_pred == 4] = "D"
y_pred[y_pred == 5] = "E"
#y_pred[y_pred == 6] = "F"

print(y_pred)
pd.DataFrame(y_pred,index=DF_Demand.index).to_csv("cluster.csv")





#%%
fig, ax = plt.subplots(figsize=(15, 5))
colors = sns.color_palette("Set1", n_colors=n_clusters)

# クラスタラベルマップ
cluster_map = {"A": 0, "B": 1, "C": 2, "D": 3}

for cluster_label in ["A", "B", "C", "D"]:
    cluster_idx = cluster_map[cluster_label]
    cluster_series = []

    for series_idx in range(len(y_pred)):
        if y_pred[series_idx] == cluster_label:
            demand_series = List_Demand[series_idx].values
            max_val = demand_series.max()

            if max_val == 0:
                continue  # 0で割るの避けるためスキップ

            norm_series = demand_series / max_val  # 正規化
            duration_curve = np.sort(norm_series)[::-1]  # 降順ソート（Duration Curve）
            cluster_series.append(duration_curve)

    if len(cluster_series) == 0:
        continue

    # 長さをそろえる（最短の長さに揃える）
    min_len = min(len(s) for s in cluster_series)
    cluster_series = [s[:min_len] for s in cluster_series]

    cluster_array = np.array(cluster_series)
    avg_curve = cluster_array.mean(axis=0)

    ax.plot(avg_curve, label=cluster_label, linewidth=2, color=colors[cluster_idx])

# 軸設定
ax.set_xlabel("Sorted Time Index (Duration Curve)")
ax.set_ylabel("Normalized Demand [-]")
ax.set_title("Cluster-wise Average Duration Curve (Normalized, Full Period)")
ax.legend(title="Cluster")
ax.grid(True, linestyle="--", alpha=0.6)

plt.tight_layout()
plt.savefig("IMG/cluster_avg_durationcurve_normalized_fullperiod.png", bbox_inches="tight")
plt.show()



#%%
# クラスタリング結果の可視化

for cluster_idx in range(n_clusters):
    fig1,ax1 = plt.subplots()
    fig2,ax2 = plt.subplots()
    list_error = []
    s = 0
    for series_idx in range(len(y_pred)):
        if y_pred[series_idx] == cluster_idx:
            ax1.plot(nm_demanddata[series_idx], "k-", alpha=0.1)
            ax1.set_ylim([0,1])
            list_error.append(sum(abs(km.cluster_centers_[cluster_idx].ravel()-nm_demanddata[series_idx])))
            if s<10:
                ax2.plot(List_partDemand[series_idx].values, "k-", alpha=0.3)
                s +=1
    ax1.plot(km.cluster_centers_[cluster_idx].ravel(), "r-")
    ax1.set_xlim([0,N])
    ax1.set_xticks(np.arange(0,N+N/10,N/10))
    ax1.set_xticklabels(range(0,110,10))
    print("Num EVs in cluster", str(cluster_idx),sum(y_pred==cluster_idx))
    
    
    ax1.set_xlabel("Percent of annual time[%]")
    ax1.set_ylabel("Normrized Demand[-]")
    
    plt.savefig("IMG/cluster2_"+str(cluster_idx)+".png")
    plt.show()
    print((np.array(list_error).mean()))
#%%
for cluster_idx in range(n_clusters):
    # Initialize figures
    fig1, ax1 = plt.subplots()
    fig2, ax2 = plt.subplots()
    list_error = []
    sample_indices = []  # To store indices and errors

    # Iterate through time-series data
    for series_idx in range(len(y_pred)):
        if y_pred[series_idx] == cluster_idx+1:
            # Plot normalized demand data for the cluster
            ax1.plot(nm_demanddata[series_idx], "k-", alpha=0.1)
            ax1.set_ylim([0, 1])

            # Compute error and append to list
            error = np.abs(km.cluster_centers_[cluster_idx].ravel() - nm_demanddata[series_idx])*2
            list_error.append(np.sqrt(np.mean(error)))
            print(error)
            # Save the index and its corresponding error
            sample_indices.append((series_idx, error))

    
    # Add cluster center to the first plot
    ax1.plot(km.cluster_centers_[cluster_idx].ravel(), "r-")
    ax1.set_xlim([0, N])
    ax1.set_xticks(np.arange(0, N + N / 10, N / 10))
    #ax1.set_xticklabels(range(0, 110, 10))

    # Print cluster details
    num_evs = np.sum(y_pred == cluster_idx+1)
    print(f"Num EVs in cluster {cluster_idx}: {num_evs}")

    # Set labels and save plot
    ax1.set_xlabel("Percent of annual time [%]")
    ax1.set_ylabel("Normalized Demand [-]")
    plt.savefig(f"IMG/cluster2_{cluster_idx}.png")
    plt.show()

    # Print mean error
    mean_error = np.mean(list_error)
    print(f"Mean error for cluster {cluster_idx}: {mean_error:.2f}")

#%%
sns.set_palette("Set1") 

fig1, ax1 = plt.subplots(figsize=(12, 4))  # サイズ調整

cluster_label={1:"A",2:"B",3:"C",4:"D",5:"E",6:"F"}

# 曜日＋時間ラベルを作成
weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
xticks = np.arange(0, 24 * 7, 12)  # 12時間ごとにラベル
xticklabels = [f"{weekdays[i//24]} {i%24}h" for i in xticks]

# クラスターのプロット
for cluster_idx in range(n_clusters):
    ax1.plot(km.cluster_centers_[cluster_idx].ravel(), label=cluster_label[cluster_idx+1], linewidth=2)

# 軸ラベル・目盛設定
ax1.set_xticks(xticks)
ax1.set_xticklabels(xticklabels, rotation=45)
ax1.set_xlabel("Time of Week")
ax1.set_ylabel("Normalized Demand [-]")

# グリッドを追加
ax1.grid(True, linestyle="--", alpha=0.6)

# 凡例を枠外に配置
ax1.legend(loc="upper left", bbox_to_anchor=(1, 1),title="Patterns")

# 保存・表示
plt.tight_layout()
plt.savefig("IMG/all_clusters.png", bbox_inches="tight")
plt.show()

#%%
for cluster_idx in range(n_clusters):
    print(cluster_idx)
    list_error = []
    s = 0
    for series_idx in range(len(y_pred_num)):
        #print(y_pred_num[series_idx])
        if y_pred_num[series_idx] == cluster_idx:
            nm_demanddata[series_idx]
            #print(km.cluster_centers_[cluster_idx].ravel())
            #print(nm_demanddata[series_idx])
            list_error.append(np.mean(abs(km.cluster_centers_[cluster_idx].ravel()-nm_demanddata[series_idx])))
    print(len(list_error))
    print(np.mean(list_error))








# %%
