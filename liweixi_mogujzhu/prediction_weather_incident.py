import urllib.request
import json
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import dml
import prov.model
import datetime
import uuid
import pandas as pd
import numpy
from sklearn.preprocessing import KBinsDiscretizer, MinMaxScaler
from sklearn.utils import shuffle
from sklearn import linear_model
from sklearn import svm
from sklearn import ensemble
# This script use the data of daily weather (temperature, rain, wind etc.) and machine learning methods to predict
# the risk of daily fire incident
class prediction_weather_incident(dml.Algorithm):
    contributor = 'liweixi_mogujzhu'
    reads = ['liweixi_mogujzhu.weather_fire_incident_transformation']
    writes = ['liweixi_mogujzhu.prediction_weather_incident']

    @staticmethod
    def execute(trial=False):
        '''Retrieve some data sets (not using the API here for the sake of simplicity).'''
        startTime = datetime.datetime.now()

        # Set up the database connection.
        client = dml.pymongo.MongoClient()
        repo = client.repo
        repo.authenticate('liweixi_mogujzhu', 'liweixi_mogujzhu')
        repo.dropCollection("prediction_weather_incident")
        repo.createCollection("prediction_weather_incident")
        # Create the training data and target
        data_name = 'liweixi_mogujzhu.weather_fire_incident_transformation'
        data = pd.DataFrame(list(repo[data_name].find()))
        data['LSCORE'] = data['NINCIDENT']
        data['TDIFF'] = data["TMAX"]-data["TMIN"]
        X = data[["TAVG","TDIFF","PRCP","SNOW","AWND"]]
        y = data["LSCORE"].astype(float)
        print(X)
        print(y)
        # Scale the data to range [0,1]
        min_max_scaler = MinMaxScaler()
        x_scaled = numpy.array(min_max_scaler.fit_transform(X.values))
        y_scaled = numpy.array(min_max_scaler.fit_transform(y.values.reshape(-1,1)))
        kbd = KBinsDiscretizer(n_bins=3,encode='ordinal',strategy='quantile')
        y_scaled = kbd.fit_transform(y_scaled)
        # Shuffle the data and create the training set and testing set
        X_shuffled, y_shuffled = shuffle(x_scaled,y_scaled)
        X_train = X_shuffled[:int(X.shape[0]*0.8)]
        y_train = y_shuffled[:int(X.shape[0]*0.8)].ravel()
        X_test = X_shuffled[int(X.shape[0]*0.8):]
        y_test = y_shuffled[int(X.shape[0]*0.8):].ravel()
        classifiers = [
            linear_model.SGDClassifier(),
            linear_model.LogisticRegression(),
            svm.SVC(),
            ensemble.AdaBoostClassifier(),
            ensemble.BaggingClassifier(),
            ensemble.RandomForestClassifier(),
            ensemble.GradientBoostingClassifier()
            ]
        for item in classifiers:
            print(item)
            clf = item
            clf.fit(X_train, y_train)
            print("Training accuracy:",clf.score(X_train, y_train),"Base: 0.33")
            print("Testing accuracy:",clf.score(X_test,y_test),"Base: 0.33")
            print(clf.predict(X_test))

        insert_data = pd.DataFrame(data['DATE'])
        model = ensemble.GradientBoostingClassifier()
        model.fit(X_train, y_train)
        pred = model.predict(x_scaled)
        pred = pd.DataFrame(pred).replace(0.0, "LOW").replace(1.0,"MID").replace(2.0,"HIGH")
        print(pred)
        insert_data["PRED"]=pred
        repo['liweixi_mogujzhu.prediction_weather_incident'].insert_many(insert_data.to_dict('records'))
        repo['liweixi_mogujzhu.prediction_weather_incident'].metadata({'complete': True})
        print(repo['liweixi_mogujzhu.prediction_weather_incident'].metadata())
        repo.logout()
        endTime = datetime.datetime.now()
        return {"start": startTime, "end": endTime}

    @staticmethod
    def provenance(doc=prov.model.ProvDocument(), startTime=None, endTime=None):
        '''
            Create the provenance document describing everything happening
            in this script. Each run of the script will generate a new
            document describing that invocation event.
            '''

        # Set up the database connection.
        client = dml.pymongo.MongoClient()
        repo = client.repo
        repo.authenticate('alice_bob', 'alice_bob')
        doc.add_namespace('alg', 'http://datamechanics.io/algorithm/')  # The scripts are in <folder>#<filename> format.
        doc.add_namespace('dat', 'http://datamechanics.io/data/')  # The data sets are in <user>#<collection> format.
        doc.add_namespace('ont',
                          'http://datamechanics.io/ontology#')  # 'Extension', 'DataResource', 'DataSet', 'Retrieval', 'Query', or 'Computation'.
        doc.add_namespace('log', 'http://datamechanics.io/log/')  # The event log.
        doc.add_namespace('bdp', 'https://data.cityofboston.gov/resource/')

        this_script = doc.agent('alg:alice_bob#example',
                                {prov.model.PROV_TYPE: prov.model.PROV['SoftwareAgent'], 'ont:Extension': 'py'})
        resource = doc.entity('bdp:wc8w-nujj',
                              {'prov:label': '311, Service Requests', prov.model.PROV_TYPE: 'ont:DataResource',
                               'ont:Extension': 'json'})
        get_found = doc.activity('log:uuid' + str(uuid.uuid4()), startTime, endTime)
        get_lost = doc.activity('log:uuid' + str(uuid.uuid4()), startTime, endTime)
        doc.wasAssociatedWith(get_found, this_script)
        doc.wasAssociatedWith(get_lost, this_script)
        doc.usage(get_found, resource, startTime, None,
                  {prov.model.PROV_TYPE: 'ont:Retrieval',
                   'ont:Query': '?type=Animal+Found&$select=type,latitude,longitude,OPEN_DT'
                   }
                  )
        doc.usage(get_lost, resource, startTime, None,
                  {prov.model.PROV_TYPE: 'ont:Retrieval',
                   'ont:Query': '?type=Animal+Lost&$select=type,latitude,longitude,OPEN_DT'
                   }
                  )

        lost = doc.entity('dat:alice_bob#lost',
                          {prov.model.PROV_LABEL: 'Animals Lost', prov.model.PROV_TYPE: 'ont:DataSet'})
        doc.wasAttributedTo(lost, this_script)
        doc.wasGeneratedBy(lost, get_lost, endTime)
        doc.wasDerivedFrom(lost, resource, get_lost, get_lost, get_lost)

        found = doc.entity('dat:alice_bob#found',
                           {prov.model.PROV_LABEL: 'Animals Found', prov.model.PROV_TYPE: 'ont:DataSet'})
        doc.wasAttributedTo(found, this_script)
        doc.wasGeneratedBy(found, get_found, endTime)
        doc.wasDerivedFrom(found, resource, get_found, get_found, get_found)

        repo.logout()

        return doc



# # This is example code you might use for debugging this module.
# # Please remove all top-level function calls before submitting.
prediction_weather_incident.execute()
# doc = example.provenance()
# print(doc.get_provn())
# print(json.dumps(json.loads(doc.serialize()), indent=4))
#
#
# ## eof