from hurry.filesize import size
import pandas as pd
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import time

load_dotenv()

JACKETT_API_KEY = os.environ.get('JACKETT_API_KEY')
JACKETT_URL = os.environ.get('JACKETT_URL')

def indexerList(flag):
    r = requests.get(JACKETT_URL + "/api/v2.0/indexers/?apikey=" + JACKETT_API_KEY)
    print(r)
    j = r.json()
    catList = []
    configuredIndexersList = []
    categoryList=[]
    indexers = pd.DataFrame.from_dict(j)

    for row in indexers.itertuples():
        if (row.configured == True):
            catList.append(row.caps)
            configuredIndexersList.append([row.id, row.name])
    maxCategory = max(catList, key=len)
    for x in range (0,len(maxCategory)):
        categoryList.append([maxCategory[x]['ID'], maxCategory[x]['Name']])

    #convert list of lists to list of tupples
    configuredIndexersList = [tuple(l) for l in configuredIndexersList]
    categoryList = [tuple(l) for l in categoryList]
    if flag==1:
        return categoryList
    if flag==2:
        return configuredIndexersList
    else:
        return [("error","error")]


def searchQuery(searchTerm, categoryList, indexerList):
    print(searchTerm)
    print(categoryList)
    print(indexerList)
    categoryList=",".join(categoryList)
    indexerList=",".join(indexerList)

    if(categoryList=="" and indexerList==""):
        r = requests.get(
            JACKETT_URL + "/api/v2.0/indexers/all/results?apikey=" + JACKETT_API_KEY + "&Query=" + searchTerm)
    elif(categoryList==""):
        r = requests.get(
            JACKETT_URL + "/api/v2.0/indexers/all/results?apikey=" + JACKETT_API_KEY + "&Query=" + searchTerm + "&Tracker[]=" + indexerList)
    elif(indexerList==""):
        r = requests.get(
            JACKETT_URL + "/api/v2.0/indexers/all/results?apikey=" + JACKETT_API_KEY + "&Query=" + searchTerm + "&Category[]=" + categoryList)
    else:
        r = requests.get(
            JACKETT_URL + "/api/v2.0/indexers/all/results?apikey=" + JACKETT_API_KEY + "&Query=" + searchTerm + "&Category[]=" + categoryList + "&Tracker[]="
            + indexerList)
    
    j=json.loads(r.text)
    #(j['Results'][0])
    resultsdf=pd.json_normalize(j['Results'])
    indexerdf=pd.json_normalize(j['Indexers'])
    if resultsdf.empty:
        return(resultsdf, "No results found")
    resultsdf.drop(
        [
            'FirstSeen',
            'BlackholeLink',
            'TrackerId',
            'TrackerType',
            'Guid',
            'Category',
            'Grabs',
            'Description',
            'RageID',
            'TVDBId',
            'Imdb',
            'TMDb',
            'Author',
            'BookTitle',
            'Poster',
            'MinimumRatio',
            'MinimumSeedTime',
            'DownloadVolumeFactor',
            'UploadVolumeFactor',
            'Gain',
            'Files',
            'TVMazeId',
            'TraktId', 
            'DoubanId',
            'Genres', 
            'Year', 
            'Publisher', 
            'Artist', 
            'Album', 
            'Label', 
            'Track'
        ],
        axis=1,
        inplace=True
    )

    resultsdf.insert(3, 'Readable Size', None)
    resultsdf = resultsdf[
        [
            'Title',
            'CategoryDesc', 
            'Tracker',
            'PublishDate',
            'Size',
            'Readable Size',
            'Seeders', 
            'Peers', 
            'Link', 
            'Details',
            'InfoHash', 
            'MagnetUri'
        ]
    ]
    for idx in resultsdf.index:

        readable_size = resultsdf.at[idx, 'Size']
        resultsdf.at[idx, 'Readable Size'] = size(int(readable_size))

        torrenturl = resultsdf.at[idx, 'Link']
        infohash = resultsdf.at[idx, 'InfoHash']
        magneturi = resultsdf.at[idx, 'MagnetUri']

        if torrenturl is None:
            if magneturi is not None:
                resultsdf.at[idx, 'Link'] = magneturi
            elif infohash is not None:
                resultsdf.at[idx, 'Link'] = "magnet:?xt=urn:btih:" + infohash.lower()

        torrenturl = resultsdf.at[idx, 'Link']
        resultsdf.at[idx, 'Details'] = "<a href=" + resultsdf.at[idx, 'Details'] + ">Link</a>"
        resultsdf.at[idx, 'Link'] = "<a href=" + torrenturl + ">Link</a>"
        resultsdf.at[idx, 'PublishDate'] = datetime.fromisoformat(resultsdf.at[idx, 'PublishDate']).date()
    resultsdf.drop(
        ['MagnetUri','InfoHash'],
        axis=1,
        inplace=True
    )

    statusString=""
    for x in indexerdf.itertuples():
        # x: <class 'pandas.core.frame.Pandas'>
        # Pandas(Index=0, ID='rutracker', Name='RuTracker', Status=2, Results=50, Error=None) 

        if x.Status == 2:
            statusString += f"{x.Name}: {x.Results} results"
        if x.Status == 1:
            statusString += f"{x.Name}: Error: {x.Error}"

    statusString = statusString.rstrip(', ')


    return(resultsdf, statusString)
