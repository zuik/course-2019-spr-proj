import dml
import datetime
import json
import prov.model
import pprint
import uuid
from math import sin, cos, sqrt, atan2, radians


class CvsWalEviction(dml.Algorithm):

    contributor = "henryhcy_jshen97_leochans_wangyp"
    reads = ['henryhcy_jshen97_leochans_wangyp.cvs',
             'henryhcy_jshen97_leochans_wangyp.walgreen',
             'henryhcy_jshen97_leochans_wangyp.eviction']
    writes = ['henryhcy_jshen97_leochans_wangyp.cvsEviction',
              'henryhcy_jshen97_leochans_wangyp.walgreenEviction']

    @staticmethod
    def execute(trial=False):

        start_time = datetime.datetime.now()

        # set up database connection
        client = dml.pymongo.MongoClient()
        repo = client.repo
        repo.authenticate('henryhcy_jshen97_leochans_wangyp', 'henryhcy_jshen97_leochans_wangyp')

        # create the result collections
        repo.dropCollection('cvsEviction')
        repo.dropCollection('walgreenEviction')
        repo.createCollection('cvsEviction')
        repo.createCollection('walgreenEviction')

        # pick those evictions that are within 15 km of Boston and insert = 136
        for document in repo.henryhcy_jshen97_leochans_wangyp.eviction.find():
            # R is the approximate radius of the earth in km
            # @see Haversine formula for latlng distance
            # All trig function in python use radian
            R = 6373.0

            lat_bos = 42.361145
            lng_bos = -71.057083

            lat = document['latitude']
            lng = document['longitude']

            dlon = lng_bos - lng
            dlat = lat_bos - lat
            a = sin(dlat / 2) ** 2 + cos(lat) * cos(lat_bos) * sin(dlon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))

            distance = R * c

            if (distance < 15):
                d = {
                    'evict_id': document['id'],
                    'location': [document['latitude'], document['longitude']],
                    'zip_code': "0"+document['zip']
                }
                repo['henryhcy_jshen97_leochans_wangyp.cvsEviction'].insert_one(d)
                repo['henryhcy_jshen97_leochans_wangyp.walgreenEviction'].insert_one(d)

        # insert cvs within 15 km of boston
        for item in repo.henryhcy_jshen97_leochans_wangyp.cvs.find():
            d = {
                'name': 'CVS',
                'location': item['geometry']['location'],
                'place_id': item['place_id'],
                'rating': item['rating'] if 'rating' in item.keys() else None,
                'rating_count': item['user_ratings_total'] if 'user_ratings_total' in item.keys() else None
            }
            repo['henryhcy_jshen97_leochans_wangyp.cvsEviction'].insert_one(d)

        repo['henryhcy_jshen97_leochans_wangyp.cvsEviction'].metadata({'complete': True})
        print(repo['henryhcy_jshen97_leochans_wangyp.cvsEviction'].metadata())

        # insert walgreen within 15 km of boston
        for item in repo.henryhcy_jshen97_leochans_wangyp.walgreen.find():
            d = {
                'name': 'Walgreen',
                'location': item['geometry']['location'],
                'place_id': item['place_id'],
                'rating': item['rating'] if 'rating' in item.keys() else None,
                'rating_count': item['user_ratings_total'] if 'user_ratings_total' in item.keys() else None
            }
            repo['henryhcy_jshen97_leochans_wangyp.walgreenEviction'].insert_one(d)

        repo['henryhcy_jshen97_leochans_wangyp.WalgreenEviction'].metadata({'complete': True})
        print(repo['henryhcy_jshen97_leochans_wangyp.WalgreenEviction'].metadata())

        # debug & check structure
        #for document in repo.henryhcy_jshen97_leochans_wangyp.walgreenEviction.find():
        #    pprint.pprint(document)
        #print(repo.henryhcy_jshen97_leochans_wangyp.walgreenEviction.count())

        #for document in repo.henryhcy_jshen97_leochans_wangyp.cvsEviction.find():
        #    pprint.pprint(document)
        #print(repo.henryhcy_jshen97_leochans_wangyp.cvsEviction.count())

        repo.logout()

        end_time = datetime.datetime.now()

        return {"start": start_time, "end": end_time}

    @staticmethod
    def provenance(doc=prov.model.ProvDocument(), start_time=None, end_time=None):
        '''
        Create the provenance document describing everything happening
        in this script. Each run of the script will generate a new
        document describing that invocation event.
        '''

        client = dml.pymongo.MongoClient()
        repo = client.repo
        repo.authenticate('henryhcy_jshen97_leochans_wangyp', 'henryhcy_jshen97_leochans_wangyp')

        doc.add_namespace('alg', 'http://datamechanics.io/algorithm/')  # The scripts are in <folder>#<filename> format.
        doc.add_namespace('dat', 'http://datamechanics.io/data/')  # The data sets are in <user>#<collection> format.
        doc.add_namespace('ont', 'http://datamechanics.io/ontology#')  # 'Extension', 'DataResource', 'DataSet', 'Retrieval', 'Query', or 'Computation'.
        doc.add_namespace('log', 'http://datamechanics.io/log/')  # The event log.

        this_script = doc.agent('alg:henryhcy_jshen97_leochans_wangyp#CvsWalEviction',
                                {prov.model.PROV_TYPE: prov.model.PROV['SoftwareAgent'], 'ont:Extension': 'py'})
        resource_cvs = doc.entity('dat:cvs', {'prov:label': 'CVS Boston', prov.model.PROV_TYPE: 'ont:DataSet'})
        resource_wal = doc.entity('dat:wal', {'prov:label': 'Walgreen Boston', prov.model.PROV_TYPE: 'ont:DataSet'})
        resource_evi = doc.entity('dat:evi', {'prov:label': 'Eviction Boston', prov.model.PROV_TYPE: 'ont:DataSet'})
        combine_cvs = doc.activity('log:uuid' + str(uuid.uuid4()), start_time, end_time)
        combine_wal = doc.activity('log:uuid' + str(uuid.uuid4()), start_time, end_time)

        doc.wasAssociatedWith(combine_cvs, this_script)
        doc.usage(combine_cvs, resource_cvs, start_time, None, {prov.model.PROV_TYPE: 'ont:Computation'})
        doc.usage(combine_cvs, resource_evi, start_time, None, {prov.model.PROV_TYPE: 'ont:Computation'})

        doc.wasAssociatedWith(combine_wal, this_script)
        doc.usage(combine_wal, resource_wal, start_time, None, {prov.model.PROV_TYPE: 'ont:Computation'})
        doc.usage(combine_wal, resource_evi, start_time, None, {prov.model.PROV_TYPE: 'ont:Computation'})

        cvsEvictoin = doc.entity('dat:henryhcy_jshen97_leochans_wangyp#cvsEviction', {prov.model.PROV_LABEL: 'Combine CVS Eviction', prov.model.PROV_TYPE: 'ont:DataSet'})
        doc.wasAttributedTo(cvsEvictoin, this_script)
        doc.wasGeneratedBy(cvsEvictoin, combine_cvs, end_time)
        doc.wasDerivedFrom(cvsEvictoin, resource_cvs, combine_cvs, combine_cvs, combine_cvs)
        doc.wasDerivedFrom(cvsEvictoin, resource_evi, combine_cvs, combine_cvs, combine_cvs)

        walEvictoin = doc.entity('dat:henryhcy_jshen97_leochans_wangyp#walEviction', {prov.model.PROV_LABEL: 'Combine Walgreen Eviction', prov.model.PROV_TYPE: 'ont:DataSet'})
        doc.wasAttributedTo(walEvictoin, this_script)
        doc.wasGeneratedBy(walEvictoin, combine_wal, end_time)
        doc.wasDerivedFrom(walEvictoin, resource_wal, combine_wal, combine_wal, combine_wal)
        doc.wasDerivedFrom(walEvictoin, resource_evi, combine_wal, combine_wal, combine_wal)
        repo.logout()

        return doc

# debug
'''
CvsWalEviction.execute()
doc = CvsWalEviction.provenance()
print(doc.get_provn())
print(json.dumps(json.loads(doc.serialize()), indent=4))
'''
