import pandas as pd

df = pd.read_csv("illumina450k_manifest.csv") 

dfMarkPos = df[['CHR', 'MAPINFO', 'IlmnID']].dropna()
dfMarkPos = dfMarkPos.rename(columns={
    'CHR': 'chrName',
    'MAPINFO': 'markPos',
    'IlmnID': 'markName'
})
#print(dfMarkPos.head())
dfMarkPos.to_csv("dfMarkPos.csv", index=False)