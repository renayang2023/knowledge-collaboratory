import argparse

import pandas as pd
from nanopub import NanopubClient, Publication
from pyshex import ShExEvaluator
from rdflib import FOAF, RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DC, DCTERMS, PROV, RDFS, VOID, XSD

from nanopub_utils import (BIOLINK, DCAT, MLS, NP, NP_URI, NPX, PAV, PROV,
                           SCHEMA, SKOS, create_nanopub_index, init_graph,
                           shex_validation)

# Done, Nanopub Index published to http://purl.org/np/RAaZp4akBZI6FuRzIpeksyYxTArOtxqmhuv9on-YssEzA 

# Get arguments
parser = argparse.ArgumentParser(description='Publish nanopublications.')
parser.add_argument('--publish', action='store_true',
                    help='Publish nanopubs (default: False)')
parser.add_argument('--validate', action='store_true',
                    help='Validate nanopubs wih PyShEx (default: False)')
args = parser.parse_args()


# Initialize the nanopub client using the encrypted keys in the ~/.nanopub folder
np_client = NanopubClient()
# np_client = NanopubClient(
#     profile_path='/home/vemonet/.not_nanopub/profile.yml',
#     sign_explicit_private_key=True,
# )

CREATOR_ORCID = 'https://orcid.org/0000-0002-7641-6446'
association_uri = NP['association']
study_context_uri = NP['context']


# https://docs.google.com/spreadsheets/d/1fCykLEgAd2Z7nC9rTcW296KtBsFBBZMD8Yghcwv4WaE/edit#gid=1574253813
googledocs_id = '1fCykLEgAd2Z7nC9rTcW296KtBsFBBZMD8Yghcwv4WaE'
sheet = 'Load'
# Build URL to download CSV from google docs
googledocs_url = 'https://docs.google.com/spreadsheets/d/' + googledocs_id + '/gviz/tq?tqx=out:csv&sheet=' + sheet

# Load csv to a pandas dataframe from the URL
df = pd.read_csv(googledocs_url)
# print(df)

np_list = []
for index, row in df.iterrows():
    g = init_graph()
    g.add( (association_uri, RDF.type, BIOLINK.ChemicalToDiseaseOrPhenotypicFeatureAssociation ) )
    g.add( (association_uri, BIOLINK.category, BIOLINK.ChemicalToDiseaseOrPhenotypicFeatureAssociation ) )
    g.add( (association_uri, RDFS.label, Literal(str(row['context']).strip())) )

    # Add drug as subject
    drug_uri = URIRef('http://identifiers.org/drugbank/' + row['drugbank_id'].strip())
    g.add( (association_uri, RDF.subject, drug_uri) )

    # Add disease as object (use OBO or identifiergs.org URI? http://purl.obolibrary.org/obo/MONDO_0002491)
    # disease_uri = URIRef('https://identifiers.org/' + row['mondo_id'].replace('_', ':'))
    disease_uri = URIRef(row['mondo_URL'].strip())
    g.add( (association_uri, RDF.object, disease_uri) )

    # Define predicate/relation: BioLink treats/OffLabel drug indication?
    g.add( (association_uri, RDF.predicate, BIOLINK.treats) )
    # Off-label 
    relation_uri = 'http://purl.obolibrary.org/obo/NCIT_C94303'
    # Off-Label Use
    # relation_uri = 'http://id.nlm.nih.gov/mesh/D056687'
    g.add( (association_uri, BIOLINK.relation, URIRef(relation_uri)) )

    # Information about the dataset providing of the statement
    knowledge_provider_uri = URIRef('https://w3id.org/biolink/infores/knowledge-collaboratory')
    knowledge_source_uri = URIRef('https://w3id.org/um/OffLabelDrugIndications')
    # primary_source_uri = 'https://docs.google.com/spreadsheets/d/1fCykLEgAd2Z7nC9rTcW296KtBsFBBZMD8Yghcwv4WaE/edit#gid=428566902'
    g.add( (association_uri, BIOLINK.aggregator_knowledge_source, knowledge_provider_uri) )
    # TODO: put in prov
    # g.add( (association_uri, BIOLINK['publications'], knowledge_source_uri) )

    # Infos about the indication evidence publication
    publication = row['URL Complete'].strip().replace('https://pubmed.ncbi.nlm.nih.gov/', 'http://www.ncbi.nlm.nih.gov/pubmed/')
    g.add( (association_uri, BIOLINK.publications, URIRef(publication) ) )
    
    # g.add( (association_uri, BIOLINK['description'], Literal(row['context'])) )
    g.add( (association_uri, RDFS.label, Literal(str(row['context']).strip())) )
    g.add( (association_uri, BIOLINK.has_population_context, study_context_uri) )

    # Target group in the related publication
    g.add( (study_context_uri, RDF.type, BIOLINK.Cohort) )
    g.add( (study_context_uri, BIOLINK.category, BIOLINK.Cohort) )
    g.add( (study_context_uri, RDFS.label, Literal(row['targetGroup'].strip())) )
    if (pd.notna(row['hasPhenotype'])):
        g.add( (study_context_uri, BIOLINK.has_phenotype, URIRef(row['hasPhenotype'].strip())) )

    # Types for drug and disease
    g.add( (drug_uri, RDF.type, BIOLINK.Drug) )
    g.add( (disease_uri, RDF.type, BIOLINK.Disease) )
    g.add( (drug_uri, BIOLINK.category, BIOLINK.Drug) )
    g.add( (disease_uri, BIOLINK.category, BIOLINK.Disease) )
    # Add labels for drug and disease
    g.add( (drug_uri, RDFS.label, Literal(row['drugbank_name'].strip())) )
    g.add( (disease_uri, RDFS.label, Literal(row['mondo_name'].strip())) )

    # Add template in pub info
    pubinfo = Graph()
    pubinfo.add( (
        URIRef('http://purl.org/nanopub/temp/mynanopub#'), 
        URIRef('https://w3id.org/np/o/ntemplate/wasCreatedFromTemplate'), 
        URIRef('http://purl.org/np/RAhNHZw6Urw_Mccs4qy6Ws3C9CRuaHpQx8AwuApbWkqnY')
    ) )
    pubinfo.add( (
        URIRef('https://w3id.org/biolink/vocab/'),
        URIRef('http://purl.org/pav/version'), 
        Literal('2.3.0')
    ) )

    # Add provenance infos
    prov = Graph()
    prov.add( (
        NP['assertion'], 
        PROV.wasAttributedTo,
        URIRef(CREATOR_ORCID)
    ) )
    # prov.add( (
    #     NP['assertion'],
    #     PROV.hadPrimarySource,
    #     knowledge_source_uri
    # ) )

    publication = np_client.create_publication(
        assertion_rdf=g,
        provenance_rdf=prov,
        pubinfo_rdf=pubinfo
    )
    
    if args.publish:
        published_info = np_client.publish(publication)
        print(published_info['nanopub_uri'])
    else:
        print(publication._rdf.serialize(format='trig'))
        signed_file = np_client.sign(publication)
        published_info = {'nanopub_uri': f'http://np#{str(len(np_list))}'}

    np_list.append(published_info['nanopub_uri'])
    print(str(len(np_list)))

    if len(np_list) == 1:
        print('🔬 One of the nanopub published:')
        # print(publication._rdf.serialize(format='trig').decode('utf-8'))
        print(publication._rdf.serialize(format='trig'))

        if args.validate:
            # Validate the 1st with ShEx
            shex_validation(
                g,
                start=str(BIOLINK.ChemicalToDiseaseOrPhenotypicFeatureAssociation),
                focus=str(association_uri)
                # start=str(BIOLINK.Drug),
                # focus=str(URIRef('http://identifiers.org/drugbank/DB01148'))
            )

    if not args.publish and len(np_list) >= 10:
        break

# Print the list of published np URIs in case we need to reuse it to republish the np index 
print('["' + '", "'.join(np_list) + '"]')

np_list = ["http://purl.org/np/RAvWwu_goLNQ9uZBPhes_gFvxAx0LA_juKY7xZxpJ9qnw", "http://purl.org/np/RAuR4wdKBdRHB0gGmrESFPtMS7sYNvIAI0VoWHwbg4Zb4", "http://purl.org/np/RARfhwa7zPU0i5ObDVqxdiZDZzjRyk8eSKwIJNKJ8sy1k", "http://purl.org/np/RAT2bbqAWif9J1cIgrwg-WiXhAJWjWUwqFF25cR049xjM", "http://purl.org/np/RAvW1OzDIgWFgpLsVD0SpmLxV8SvOpNQ2Bif8pV2cTjnQ", "http://purl.org/np/RAQSXVmcD2B4FFWC3Qn32mXRoJsu5XVuKVldOgyIx0u0g", "http://purl.org/np/RAjPPB4YMMLippML-73UD_zGG4YzYZsmZ7V5OwiqrtIS8", "http://purl.org/np/RAMcaOBPvJgXMHW7fQd99GqgtMZzAbaFprwidSTtQAG4U", "http://purl.org/np/RAgbMhAc6358VOYDxHcxo1AB-KUR0IUdpqIHrqWTBzutY", "http://purl.org/np/RADXZgGUX-hJNbbBuAVuy1XQa94DNYUJqQdiB6BTUTxXI", "http://purl.org/np/RAe9HDCFp5nLKoB1-ZM8RkQqH6vsbkYVzhKtBigo2WInA", "http://purl.org/np/RAsD-tUNkAsaN24HSKHWntu4Ky5haFpnWkkuGTI9RWQyI", "http://purl.org/np/RASpRPyomRgMVbNPpdnQRpx4SNDzaFCKqtVYjIjBQCgT0", "http://purl.org/np/RA1NO1oir34lWpCfC8swlBk59Aydr1LtDDshvDMFp7A-g", "http://purl.org/np/RAF7eSKmd3qvMVjWWG9P6_OQI5YadKAaLdXrrOdT6a1Pk", "http://purl.org/np/RARuCA-eF8Hyt3BSQeUeyQKpznr41Cy904JbTClUEdk7o", "http://purl.org/np/RAU-61FE0zb6sGHnJ2OImYI1WTtUcb5mWGYQgDeSk9es8", "http://purl.org/np/RAJ9XxvXck7glrnm8yWlsFYO6hXUsMhJBWC_Qnn4puR6s", "http://purl.org/np/RAvlrX3IvUSC8QwqlW742I9fcYJzGRlbz5N4ZkhCgNzZ4", "http://purl.org/np/RAf9Aa3J58TooleTMG6P31VR8BiqwXlCvzr8xn8ypzDj4", "http://purl.org/np/RA9jovKmm4k8-GDJ1A8b5AoeLiXqMErrJEDAzxtdj7_Kc", "http://purl.org/np/RAfYMkuaLhAPOZv3JcUVS7P9dXte6nD5I7KhrhHyTVT5g", "http://purl.org/np/RAEQEGEhbv2cL8Itj1WRmB5NIEd-bXke5GuBIcUpuDV6g", "http://purl.org/np/RA3gD04QOmIZab1uq8ZgQfWS83YzKgRD8APNwIzxdQIzU", "http://purl.org/np/RAeGWxV6B7IxhiluXM9iRQCtLKVXKX_GL2BcvGkX7Peww", "http://purl.org/np/RA0fyZ8fV3zBUOtqA8fp1UDC1XkxTuoQ3vs2lHS4PfdpM", "http://purl.org/np/RASaLV-3Vp3_Qshu5L6AUFGUfHdytsT5ngSWwyCm6tbKY", "http://purl.org/np/RAxT6YPy6mm1ZREX3983isBn7Q_7F5awH32xgRmB01o4Q", "http://purl.org/np/RAr51ocL7mQTdpr2sHFPul6qD-taG4wjyvTYuX_Du38NI", "http://purl.org/np/RAhGvPoKh7ZIrigzeTa-sVnVei4wZPje6Uk1-gl9YEaqM", "http://purl.org/np/RAmlh-UD5BTH9UHHxiBRULviIFRaZuuQSodiQqD6xwYjA", "http://purl.org/np/RAxMllQWAV44gxk6P7oZ8HEUobEG5l9Lat_uR3HXd1OL4", "http://purl.org/np/RAC-c1xRYYS4h_0hZ3EThLiF-3TXkLSnre17qcwjYHSpM", "http://purl.org/np/RAqT38TcYUTJxjRKBx1Soy5ft4XVDrset5x8EO74vXb5I", "http://purl.org/np/RAKPcNpiIuPHH9NEcEnNprv39Ygp9tMMcSmGLHx2Qatqk", "http://purl.org/np/RA-Kwpl1C75pQzOk1cAMI6M62GDC-cO_aptCjDv9eKi20", "http://purl.org/np/RAW2Ya4LMtMOvrEFkrQs69_MxJ2HcbPexe5q88vMdfAss", "http://purl.org/np/RAhjB50ONb3apMiesQ_u7nAlw-eWIj4Wfz75p13m4cIPU", "http://purl.org/np/RAwCtvcYuNEv39Sfipj9jEJjtpxx2kjjauWTr0Y67JL8M", "http://purl.org/np/RAWgE_QLFkVI0o-sJXVvDYgiHFVmfB-JfpPWwmUAnyDwE", "http://purl.org/np/RAHjw8Sp2hkwR6jmq9LXdBsFHcOSuKh-gJKQaC_wTJIk0", "http://purl.org/np/RAWfVYFiVy59w8N69AT6tDMG7WyBatFDe8FD9dkhGC8Bw", "http://purl.org/np/RAvvkP3TNOIGW-4hsVAr9A29KUCTzllwioitcHBWYVehY", "http://purl.org/np/RA1notaYcBCEHkgAyT530zdC9-M_WGu4nEE6LD5S5GkJk", "http://purl.org/np/RAz032lXHnX7t85rb59CJCTE_oyAckU3YoqzfyJX3zcbw", "http://purl.org/np/RAJ3-d042VlDabonXnGO6SzggPUNyi-8taRzi9b9FyUsw", "http://purl.org/np/RAWRzpgYbLJTNp8Zab1Pfz-a_K99cVlSM-PwBAl18chXY", "http://purl.org/np/RAwrBmGyX4zm8g4Rx_8W0alzubO0SWpwHJnQ6YMqBgdRU", "http://purl.org/np/RA2k8_Ora2vrznjxs1ZtB7Lv_oCSL9ZQirdnEMlsJ_pg4", "http://purl.org/np/RAWIY7-nYSVjioPycgLIfIdIhcz9WWlG0GvamTDdukcrk", "http://purl.org/np/RAzvvGF-Kv0VVQluC0oGzQNIwQNkygfLYqOUYW_AaP6lA", "http://purl.org/np/RAM67tDl04DInK-peBPcgwn7Hl6d1PwTJfE2vbnDvZU-8",
 "http://purl.org/np/RAY_YGBA-Mqtd7vIzPxjh4NDQNoTTlndkZXArqFulITEU", "http://purl.org/np/RADOkA9dnQKVDSGUy7oSTq443R807dCjxA1QDG4XZR7rs", "http://purl.org/np/RAEvxhmPKit6QhrOzXeuc-5GmqShBSJ3BBKE_C_vc8MI0", "http://purl.org/np/RAeK8oG4zd9f8uuKPQdj2onKCjX7EAQLrkNShq5dJt2oU", "http://purl.org/np/RAgOGQNEybARa5zNeqepDQvz_pPyhQey0hmnOzahnOCHI", "http://purl.org/np/RAZcseMVGLjBsI4G_r8pCp0NQCFiepZXqMQ5xaQfQj7ok", "http://purl.org/np/RAbNeR3To5uXi8AMxRajUnPmA_ShEMUfc3VKpj4aGgRiQ", "http://purl.org/np/RA8r54igzcFf-AR-mF_8oWr2lNTrlWVMlWFQT7uz3DKqY", "http://purl.org/np/RAIXi2NLN-jI7EvPpr_-o6xQ2qpJLo1_YJERMqbABDIVw", "http://purl.org/np/RAroY6OKAK6Zsfwo52sPyvQsJL2_pqHaHQ8-TGNUhsq2M", "http://purl.org/np/RA4p_wjGxBKVPXtjDMPYxytDaqwAKa4ChOzjLk5ch_QWw", "http://purl.org/np/RAtV4ib1c4Uqjnk3abZhhKrvKjS13W4bN3yIwk_xLzEog", "http://purl.org/np/RAFRKhyXLxcEtMI4_rgA6ikl9mujja_mGqFtfoDybr4Fc", "http://purl.org/np/RAokkK3NglfGelVNAmEgYUe8QwWRMUNiWnCAvltIxsgKY", "http://purl.org/np/RAdFwe8zxq35Nc7UrDVNVauePhZWNa6WZ4-kII5We9pY4", "http://purl.org/np/RAgz3CJ8GbD9Tc6HMcHNUGSbO8IBcyFB3pIYcJvKDGMbg", "http://purl.org/np/RAg0iuRTrltMcZuL2CrQ6fBNmixhMezvgRQw0Rg24Ltf4", "http://purl.org/np/RATrJMfVemKY71b6OaX8P2bQbJVjxxU1bTgO_KTepDioI", "http://purl.org/np/RAJ6aMEzRE0OYtqDio4sH4m0secRibziaBPl9dTzajsqE", "http://purl.org/np/RAM5e8CsgWKP1vCCD0Na90XuLw8lcCGIe1cyoadAST5ec", "http://purl.org/np/RAsnjz0Wii8dOiNWOcK34qSHm8HlTjCJV3OJKdeu_3Edw", "http://purl.org/np/RAtSVbR5pFhP00ZMBynzxDFk1CpYwHOLMh11tHFy316zo", "http://purl.org/np/RAm3iMSLqO77JWs1umbbVaChKvY7pSuKHwqP9KpyPUlGs", "http://purl.org/np/RAWPtzlBvsUXIweHAVBYMupYSMVXxQnjLFwJ8gFHXlX8M", "http://purl.org/np/RAkbtoalfJZPCoE-PAFiGmbN_wc6fI7jnUb66nPXsWID4", "http://purl.org/np/RA023QatvnNniBQmzjfXRKvreeXNfsZirckvpGiDYjiks", "http://purl.org/np/RAFEmaF_1ZetBT7EPeFz8UPQTKY4LeN2HO8WtziMOdjaE", "http://purl.org/np/RAtMjRa8JoVyf8gX4Mzu_8LahtL7T3Uon_Q9Z5XofVg2E", "http://purl.org/np/RAE1Pr2PYgj0PqO3qBL9nuLEEyE8VWVcgZMGeKUQVCyI8", "http://purl.org/np/RALFBk1LSCuCD51ce6PQ592_zEWh8yngfBcjwb2ayY8Pw", "http://purl.org/np/RAwsRNUPTlBdzmVSDkQUuQulNVXTg0Gc-LZJao1ma78b8", "http://purl.org/np/RAGs0cPE0tJElMI_DaOS0ueV7M-jkETL2oT7kJVw7vsag", "http://purl.org/np/RArkbMDh5pqKTzD0W8j889a6nnbP71lANWb2EnveCXf-Q", "http://purl.org/np/RAW8vL5PRVLhnwuRq4G23jnRGjsFLFrWXIoAHXpr_4AkY", "http://purl.org/np/RA9dBQLgnob1pFZ_vHpavztZ7Oc6d_lPYyazU9UVNC3Gk", "http://purl.org/np/RA-eUc3B9WYNh69qOcQS7SpdJkGxLGuOY6qtGgbd4Ze6E", "http://purl.org/np/RAOsQ6z_ber_HjXajwPVptVA5w2GIZZQw035rqLA-fCYY", "http://purl.org/np/RAwJUmgk2tiHU-OIXhW-0X25q-KNnS4nTIFE9aBp6m68c", "http://purl.org/np/RAyBkyRnoET9XWc8t5OpZ3F9UDRMELVh8P8iZ1-x4ELA0", "http://purl.org/np/RAHAn3W8b4XBnGg_Y-7SI_9w1BfMRdD-Exre9Cu43I4Fw", "http://purl.org/np/RA8Qa58Mpl3EN00A75CMaIH5ucoPHF1BV7I6YxQY_XJKk", "http://purl.org/np/RAowKcMSMkMM5iOyR1YTdgKrojEBD5McH_8PthVu9asVw", "http://purl.org/np/RAn43F0vVnm0xArzwMZO9LX1geOzctEZbIWfKMRJrm-Go", "http://purl.org/np/RAxXZ50iURIrl6x2unpz-T5PQymVasZwEQqrKCEeJAe2Q", "http://purl.org/np/RAb2VztOSGbFFj_l_tYLPTVa4aBqCYUMQRzWXCgeNgTEw", "http://purl.org/np/RAT63vyXgtJrPWavpB5UiJvFoODu3Y-PSF26iQyDWVn5w", 
"http://purl.org/np/RAziUyifdrMM1hMeRNufY9z6RbsbrJzW-ujAlCzBGoCjU", "http://purl.org/np/RAcw80yPihjjkFEDE81KEM96Ke6QI0mrmQZPwRUyIg4Ho", "http://purl.org/np/RA0ciIaTdrepeWnIUXXuAcklaN8XID6wCXxJAFAENvifg", "http://purl.org/np/RA6boG8HuwPhCNR8L5RhhHdr0y2Mcs_QW9PdEi_vqBu2k", "http://purl.org/np/RA5gEHAYtkLYHgc2JSiukU0d9jSwiJAJ_j_xGczXi_kJ8", "http://purl.org/np/RAZoWyw5SSfLPZgWX3OP66MdrMFeSQWnhmGeJtoTUvn4U", "http://purl.org/np/RAEwN7Cio_zeBGQULUF46S4iVCF3ebX-fvwQrR4hOHxrA", "http://purl.org/np/RAVy2THIwf6I8tU45UguSLGI6BykWqOyyqxr2wk-Ah-IQ", "http://purl.org/np/RAfqXqhfidbi6eHPkHgbUOl2JtgZge0iU_YRpcCrG3dUw", "http://purl.org/np/RA8SpKEpzWTsOA1YVsUbScNmq2ZTib_DL2StrcdDFul00", "http://purl.org/np/RAOim2MDcuq0rW8acOfC2psO_4SIj_CGIKe9E5utEL7NE", "http://purl.org/np/RAjzakoJkIDXtvfoDamMsotWcnvqpoYM78oatrHmr0KIw", "http://purl.org/np/RAMVhWOJ3Y_tl-5nTr8StO_TlvBrR8e8VJFq8bkx_rRc4", "http://purl.org/np/RAOkg0axLUhFzU5wlvemOSR4s_Pwv37-ZtREb4uYNv4jE", "http://purl.org/np/RA1zn7z0KZSU4dR83KtM2T-w3pVGE5ppl9uRB96R6CeoM", "http://purl.org/np/RAoyBqNjLx1JaDy15du5RHebO10liGV5vZKKfjFZLpiUA", "http://purl.org/np/RAqVNVVYLqFIBw_Obd5Tamsis_pidqxKlsmRjjm-u68zQ", "http://purl.org/np/RAk4jPTxkDa4O127HT9z-If_8MRcvMjkqJw6UtOs2KPRw", "http://purl.org/np/RAgWZ--HwoYSJjtB0Jts_ZI9J3ANBniZuxvEKw-gijoHk", "http://purl.org/np/RABFo4lJwmjlx69B4b3IjvJ8okm-2hVGIzBz_sZ0wkub0", "http://purl.org/np/RAK9-aqPLDkg1E67iIVmXhcxmB-6_0LWGIOt7k6sZq1Tg", "http://purl.org/np/RAsr4IsJACxMhEk7mJ_hc_V2G7d9bOdkIlgcYZTyXqrBs", "http://purl.org/np/RAOAL0YYmV-PmU9PMNGCc1sVdoF-nZ5XOwP6lt1psqNKM", "http://purl.org/np/RA9xLb-4JZejB5Np-OliOh-T4ZAHXOeqdfdQQPubBx-K8", "http://purl.org/np/RAOoK9UhAHyRfjR7fFMPEhOI8JElvtY4YsiibGgC55YlE", "http://purl.org/np/RApfcWvESw2vh2LrKCzxRS9TxYrL1qYZeA16REZi-Wtx4", "http://purl.org/np/RAT5QekTLy_FhW9zr_mSEhqis3wjXqVmdnieaKYZrsQvA", "http://purl.org/np/RAQ1EqxgeY7XjR7DY5c_AOW8rBwIDX6ioC778-vZXtr9E", "http://purl.org/np/RA4ZpOwqoBpB0xUlmOL-hNPIxNubG4LcaT7SMytq-NMSM", "http://purl.org/np/RAXpQdI1ynPAyJ2Dt46RGOvuW96CzHLCDM4hcqROJ_QBQ", "http://purl.org/np/RAuAeKyOAoSnvLp6P9KCCOv-MDIGCvPOtATe5ibl7lprg", "http://purl.org/np/RALc2mrXCH2ToF6AFeLMDO-uEHfpVQnPrJ_WNfVfOhjiw", "http://purl.org/np/RAAFwVTS9zSGpyChNaKA4hQHd1RgljUS7mWA4MOn5gado", "http://purl.org/np/RAbwIS061zfp3vhExgR0eTbgpdSfzyismcOKDxlkVo21k", "http://purl.org/np/RAkZ3tJ6USLw8GTyQiZoZA1cZKyVMPqZO8gFR3oebv0Fs", "http://purl.org/np/RAj_LA3PltngoaTW2toZu69GwrPeSmTns9MnQbVAdT0rM", "http://purl.org/np/RAG9k5BaQM7A3ZJyiXeXWNDSwTvTKre8lI_ewAcXflV9A", "http://purl.org/np/RAB95WMMk-QtOi9ktJ1U9ze_r0HzUXZxYBi_CNkOM8Ufo", "http://purl.org/np/RAaKD0dXE1O7pToNkUJa_gWr7qB4Cv5hgoT1Timr290Lc", "http://purl.org/np/RAtDKN8EiPBnaNxFva0nY2P217Xv6EkNdyCfUYcUZ_tw4", "http://purl.org/np/RACsHIRjdwOobcrwSkZlMdHpjIkv7iJV3wdLpWxGZU5tg", "http://purl.org/np/RA4wGuoHOd6g950TbjajO_ZppS80n9qBxwet5TThJXH-Y", "http://purl.org/np/RADsNbpA03IpbQ6_wdHEvRxrF_0e1Rj6UvNhn4cg8vQw0", "http://purl.org/np/RA_jIY3w0W8EzoHbPWwdJzOxhFWk7O-b1JsnXYXk1wXAo", "http://purl.org/np/RAWh8wiGCqXTla-T89AvS2Ps42ksplpRL_IB15OzSL9Bg", "http://purl.org/np/RAKfyuRC58TKIB2x9ZxAr7flGpdXPRCeSSTVB0X8gyPDg", "http://purl.org/np/RAXuQTaR84Rvl0GcQ97qo9q2ho6M95iACflozMJa0QjDw", "http://purl.org/np/RAivxqIrN82fjt2drYjN4WYU31nBEU4ovLhGjDATjenOU", "http://purl.org/np/RASTGIvkxidJH1HgxcEnP5vyYkH-NdPria1stxZhJlTeI", "http://purl.org/np/RAiD1sI3Ys3D04NK7GTOSVGA18xuoNo63SSSrVDSP9mhE", "http://purl.org/np/RARLQJtD_O5nib4aKpypwAMQ8evjUBQpND76LHbDImPQU", "http://purl.org/np/RAvgOyi9C7NPX3IqH06J7dNyikYdhJ9M4S3DHPLdIjvvY", "http://purl.org/np/RA-LoMFQw27uCLs5h6erz2QmE56M-8ZjNt1DJn0K59Hos", "http://purl.org/np/RANYovXDsXwWFxR-Qqysfc6qX0LDtQ4pMTkLQ6y1wPTD4", "http://purl.org/np/RAGUVr1ZJSrlZg-jkUhfdZf117yorjcRHl9boa1C7phXc", "http://purl.org/np/RA7Ve5kl9gKGCCMMF28OqwxVaWYV6RjLbjn9KBFYAdgSQ", "http://purl.org/np/RAgg-0_Mk4-DbO_-0BTiBjddlF6Eo7cgzQNaJIM1wO5wA", "http://purl.org/np/RAdrdZLWrqriMcC7NT9E59Vn-6CjehBQkMbYoUq0zTLb8", "http://purl.org/np/RAZzkuGti6W72QWl6n_jwQXMNj4x2o0dQyS9FIv-q0mxc", "http://purl.org/np/RAMAp2V34wX7dWwG-pgP9YTU360Mgkv0N3-YYtw1GAZT0", "http://purl.org/np/RA__fG32DdGpjJdno5Z95-GyJsy8_TXquDn0kB-a4z50E", "http://purl.org/np/RAdfZh8BJxTkZBsUXH6ZgHoX9G1oUtwc5tXPUyaUSYBqI", "http://purl.org/np/RAkkNoZuYmtjchS7F-HZOluN4dtWZDTTRHisYKSI_LrCM", "http://purl.org/np/RA9aUJVFqVcV4C98yi3JsNAq2-n9vrBWb7_1JEcv1xHBc", "http://purl.org/np/RAZqHbW5C8BLjtBFAjQx5LqjDEiG5Ddn1FMuC1andCaTc", "http://purl.org/np/RAjXgOowAAQQbHIQ6lUp3-swmq5WIlFrvZUQ40HNQx_U0", "http://purl.org/np/RAwCaWfE1hMqx6htGPRppXMUP7CJnforGUPSSnuHxsmaw", "http://purl.org/np/RAGpeX-ZnyxlQ5HmNOo3QJNzHGbJSVAEWTOOeqpYtGOF4", "http://purl.org/np/RAs6cBbhWd2XQYhmzi8Ul3YpN21aEO5ywdmuHPthg9wTc", "http://purl.org/np/RA9oHGBJVgCPtHfJvMSiRFitfKGCS8PgLXYoDVvNJVZJk", "http://purl.org/np/RA6yCrrwlP65dAYAqVK2p0QCGfu1NzjR69ynoWZeeYi2E", "http://purl.org/np/RADW8nhqzJa0rmkYIiZxCZvQ998M2XJ0r22iGSqk-MzhA", "http://purl.org/np/RAcFKm51UymJ6v42PNsXifXq7YuOhlJW4BJG156bp4vCs", "http://purl.org/np/RAYXZiT2Tz9VIETzN95mjxs9PVc29l1vhLy6TI7IEiK1g", "http://purl.org/np/RAt9axC8LTTGaC_WChKCTpFl4M_QczUaMFQnxhHMaBWEA", "http://purl.org/np/RA-yxUlTiBsMKd5EnCZ5AjdF7uHuYZ94d236_ogo3cVQA", "http://purl.org/np/RAJduc_s6hV21_gw_XAzcHD-NRRu9uBVkqEkUQUqoTOa0", "http://purl.org/np/RAVO2XVqVbS5jxWwptuuQIA_AbwVR5VZHniDBTQFGFczY", "http://purl.org/np/RAVCIlzI2QvN4wvsuMmWtgwg-GGt88UfvgDuf9PpNggak", "http://purl.org/np/RALbNyJhhnWIWjXUCslXO2FGNuZm8P5wvWCXuCCTNQRyY", "http://purl.org/np/RAmBxV9NwPCJF00tOcDOvIaWVPltHn-LOIupuYkqY93fI", "http://purl.org/np/RAyYJo38dTw6Ss_FhpVjz6oxfvGmQQfDWzzNidHBxaRTs", "http://purl.org/np/RARjgImneEn8TPJepxHW0I6D_CDYvgl-ewVMp2yEITkd8", "http://purl.org/np/RA31v1IDai9s5qrUpzGAbr-6A42x3f19YN82-Fbg3n4mA", "http://purl.org/np/RAIztrMHG-yYosqB5N47FjRMlURxJBBMUwpw6xRf8onFY", "http://purl.org/np/RA-kOJcRDmtZDXRiS3BF1zxai20gt7aPt7n2MeMnNwjMA", "http://purl.org/np/RAJLJ8WuczC6uwrh7JfdKAEvqA8m-7bcSOdeAELOqKiCM", "http://purl.org/np/RAN5KmzounI2FIW1621vxLpqI6mutbnMYGqEpI06xpPnk", "http://purl.org/np/RAP1qAgf90r8AUYRvfBh2OOfvh0_8KGRiB4ONH6ZsiW90", "http://purl.org/np/RAXOfRUa4ojduoBCsaa7y1jspzdDCSi39qhClLmlKLoBQ", "http://purl.org/np/RApOJ3vxzPWK98DZsWB5ErvOYmG7uJ6MFnurHz2Ai6BBQ", "http://purl.org/np/RA4PzeAbzOv_sj_Ldexv7_Dv025KYOWCC-eD-CRY2FJLw", "http://purl.org/np/RAHEt7YmTx3srmw29GbI0mI8g5VIcsMDlcA_TFGSCVXJY", "http://purl.org/np/RAqUZr9Tj5j5o5jVM2DL74gTyV40T4CZeq6GhupgtTG38", "http://purl.org/np/RAalVmK-ClyipNQ_mLcyOIxJ5pBfZEII86RM7YuSJ90XA", "http://purl.org/np/RArAh9WAEhBOg0eCNhS--IO1FCuxGDKBhJpNWPVuAIrgg", "http://purl.org/np/RA5fghTqOqBxtvOs-k77DSpG8LmFWg4EPX2sEiOvJjEbI", "http://purl.org/np/RAMcSaqfJedr1DJLZ36OhvT65_doAbXF9HDVP3f9ZKGLw", "http://purl.org/np/RAC_56UzIPTynmNLPsfuG8IOeFR5aD9vOED2Y8XAhCN7k", "http://purl.org/np/RAYESi6U8cgczAY39TXKCzeI1Pr7Y_081rutWjaeQb0Ak", "http://purl.org/np/RAdW4VN5_UKHkIOkwlQD4PnMXQ5-pPmxcSZIx9qkNtY68", "http://purl.org/np/RA1_pfMnYwfKwdpaPSWaOdNIgfJj6usiaitfW14KzBBuk", "http://purl.org/np/RArHZARcjeWGRPOAgUWyubYL9jJ980ChBdHVJBgGWoWX4", "http://purl.org/np/RA9fwJJb0aiuU1jXJflWRhPTtbRvjnUxHjhwLmfYhIO74", "http://purl.org/np/RA3LvPLfqzVIZW4hopz2nsK0Z52t-Y1s7WFVs0de-0dnY", "http://purl.org/np/RAY8Y7aCkiEfQgD3nCfROJiyZlqGXZEPKqXFkUiZ1MyR8", "http://purl.org/np/RAiuIF9WpGj5Vu-nU9xczdG90nAx2O8iFl1K6xWRFwWVY", "http://purl.org/np/RAh1HeAxux_4GeVS_ZxCTW5RdHoqyQR2-Y5zKqF8nqP1Q", "http://purl.org/np/RA54-0Xuk_7TndjtxGXG3egqq0LajQEzoBv-7TRPM9HFk", "http://purl.org/np/RAEIvb8GGndQJkJCbw3WefR0ntOrjU3y8VS6Z4OREewqo", "http://purl.org/np/RAxAUvPgoelRCbFrOtOBtEPp7izR2DQ2_EA30fhSZb3D0", "http://purl.org/np/RAmsZxqv6cuu7R2lqIqplEczdaNFQ2D734yVCqLKYEoLk", "http://purl.org/np/RA2a2LIbzA2RE84CZOX2fhBYhw-Dz1AyWOYlwGeThAzCc", "http://purl.org/np/RAIy0aLbS1T_3gq-ag-u76LKIg7z_TKIGuD4W8KTP_t-Q", "http://purl.org/np/RAqiY5WFLzXapTGwZ39nPNYZ4Bh6Fc2I2ZpVQugax2K84", "http://purl.org/np/RAJGZCKJJAKWUHX8E7EktwNrrfblpevOYvvbm-2dn1564", "http://purl.org/np/RA7dILWFN5ecJ-z4UhEZFN8-qCRawBCaDP0o_ozDf20Go", "http://purl.org/np/RARyaWqFDihdLWcjLx7vkuUqw3sAxxjZhtWYnjLTgKQTQ", "http://purl.org/np/RAj6wpm0ysDyQiMTolMSsQiBPq0ej36qe7ENvGxcdFmSg", "http://purl.org/np/RAd5qzG3r3ToVROTXcGu_amNbv2Ig9BVBwnIswdkD_C3g", "http://purl.org/np/RA1wdolSsDlDIIS_SDqYQY3iGePHKVjDsXx_MOPFW3XOs", "http://purl.org/np/RAQCul6AGZ8syFXM2mMPJp7edQF5TYREC2RyJG7QGEPtE", "http://purl.org/np/RA06m-PyO60OB7c_g_b6TjUo--lYBkTbPSCd1-45tX98E",
 "http://purl.org/np/RA7dijBC8ks92X-NaPvJUUIcXaphL7VOcC8AXC7tDG4ao", "http://purl.org/np/RA_NnATKVZ1W5RCOAwoAUIPN_MSoxIjsZiw1OitpnXbiI", "http://purl.org/np/RAtOumTR20W0Mp3Rcqqiu3NPq87x49DVlHyG67Ni5EoAY", "http://purl.org/np/RAgbK497iHfpjUa2HW6yT_CR5xl-fKDG57rItlboLgv9I", "http://purl.org/np/RA1Rb0sb6wMF0dJbweGP5KNSALNUMs8YsL2DJ1sfEN-ME", "http://purl.org/np/RAPehdevbYkS6IWl1OMt7RYAVjZO26LmA4RxV5GWnVNuM", "http://purl.org/np/RAEC-AOXXjoFFtr0mMDRbCK1ULZghwtcEO3vryWmKGU9U", "http://purl.org/np/RAwMDR4luu3vb_OLq-bb6D_fGpE4_BtFvweRBAz6icxDk", "http://purl.org/np/RAH5L_M8sCuycTFzC9cOI5vall5vi-OZ0UOSaDQTlM9bE", "http://purl.org/np/RAeOv9OFR72bzo2f4bOENeUmm_f5xsLH5vBq_CEh4HZaw", "http://purl.org/np/RAm65ICM22ZDv5CNYGaN1pjRqvGiquOpL-FtW9F6cQ_MU", "http://purl.org/np/RAI_TM6ITgK6gmarIocSg8YDx9xbZexsr6Ol3o-pSq5_A", "http://purl.org/np/RAX-EHMKi-2dsXxRlMYKQBD6GqIZMPKR4yWAqrHddHBuA", "http://purl.org/np/RAkhptrtMv3l1CiUgtkLyLxWqA4FC0tG1m62OfG4QYQA0", "http://purl.org/np/RAZ-brC0kta0JF4r-1a4WrYWLH4JCU3NAAtaHSowrZ0yA", "http://purl.org/np/RAuUqUVYbJ97--S8lTzwYXEy5zomq4w9bCf0QdqiuORBs", "http://purl.org/np/RAh9jiHy1bJNq5I-ap-je7sbLelgwzBrKZFu4LQM51vaI", "http://purl.org/np/RAZrzwrKa4L6ox5EVJ7nhF06x9PvG8Zoba17ryToiKaQE", "http://purl.org/np/RALfpb_hJI_HVmu_3Af9LxIdFJQU280O3kxkTkMCh6TjQ", "http://purl.org/np/RAHOSBwU0F-OHKHcMMojqq6EQzGO4EC2-f8K7Iak8PKgM", "http://purl.org/np/RApskZKu7n84jCUwWNQGq6SrvZ6TSn-fe_j0SyUoxBTFM", "http://purl.org/np/RA_NUO4DtDrThDJjE8fdMq2tme8mQ8gpXyqdB8i1hGw0U", "http://purl.org/np/RAEnVQTNuRN9ZH7YAQLXVmCbWNEC3P200EE44dksnhK50", "http://purl.org/np/RA8TY3mIUE_uUNG5OxzriFo7ZGLh5LtOMRPHPm3dcdntQ", "http://purl.org/np/RAY4X2_asozKCdK12ii9Wx3jgih4zAvB1PvnrRAJspG64", "http://purl.org/np/RAQYAyez4sRcZLz-AaDDeviGAhImyYBNWl9UWP7buHIxU", "http://purl.org/np/RARZ5zQs3bfIyYeDaHHp_CvvdW_do3zD9kc8q3u5cj528", "http://purl.org/np/RAUXaMRG3jhLi3eDxGEmoSRMzo1Htw-a3uEukSj9Ck-kU", 
"http://purl.org/np/RASutZn4RkYIx0_L-xy1RiOs2iwS-nfsbhMPys4w7Zz8c", "http://purl.org/np/RA6jyMV335LVobC1vIjfr3uI9heugSLasXKUOXaMnZCxc", "http://purl.org/np/RAtomgSlbzkMmMrbo1o1POK357alBKXM4SqjeJIFI9O20", "http://purl.org/np/RAzYU1HBBKZQTFBlJADcd1cYXIdpDzoGwzBSMbB-08gLQ", "http://purl.org/np/RA-3qMJt6_k0A9QQQyZeffuupqW-M_e5j8jdkXieUmlRI", "http://purl.org/np/RA-Od-sx9fGy0JkwPykiqj5Ow3_uaRC83dp1YigQ-T-sI", "http://purl.org/np/RA-nIAqa6AJiFZVcGQkVOIFB0gIQonLBbEADvrGaFCHD8", "http://purl.org/np/RAlyQJWD0qMGmO_zhETH5p55Ss-4n-ysziyW-SxvXxTzA", "http://purl.org/np/RArOhSLzlOPHYMchJDLPb6ij-f3lCeoE15MpNQFddECSs", "http://purl.org/np/RArC9ePH8urlHBSgPjd-Xxg5Evp27K-JcMRwDoq0Vm_VI", "http://purl.org/np/RA2HoYIaWVviySloVHKbnRA9mC3XMIqBID937BFpxKrXU", "http://purl.org/np/RAkohbGcXkgD7Q_uQHX72r3NiVyt2ssFVLcy9lcFA3I8o", "http://purl.org/np/RARuC8gyFXf146qIt3_VGAFz-Yx4S7NNFAhcnUVUOwfU4", "http://purl.org/np/RAT0kYi_m3xo6SWa59GCbNnXdWQRf83MZfiI8bpOk2rIk", "http://purl.org/np/RAza6OegZBspU4MyGfe_LuRyxrhfN03TKYVHfssHHuEYE", "http://purl.org/np/RAsHDv8Y8z6E7xT3kU5fCHi8stP8BzVAcFjwpxxmpwpQM", "http://purl.org/np/RAwlUKOkdB0hlnEFIKDZZnj3Llnpi16vL85c7lnRd7t4w", "http://purl.org/np/RAZFqdakeGaMVnGpjTC_tRPZ1trWEeMiq8gy2y06u-nnk", "http://purl.org/np/RARK0SeYZgGu4sxDxSzs7MzUDvmP33GCO_z6KvgxdNwXs", "http://purl.org/np/RACXR1n429PVAJQHV3-QZQtIM2-QewVlELI6P7-jRGGkU", "http://purl.org/np/RAcRQdZuEggurjX2YpEV3eXEWwaps9nLlDWDxnPBeUHB8", "http://purl.org/np/RAMVNKLloffsR1-RehLWKwJjIURePjoHzbYd89ck_MvyQ", "http://purl.org/np/RAJH-cDm_BMiLw_iEIZNzfxQkIm7n8AzYlV3H55QAzPvM", "http://purl.org/np/RAfcdsR-O3e35JMRqwKDNkOGjH_zZxUtnMb3oiKqc2w-E", "http://purl.org/np/RAHyydSdVp_tF96LpHbCS4mEAvAu54zh7DFFm6PVRxt9I", "http://purl.org/np/RAjAeWlOFfwM5t0rKexWGDFakDQFJQMjCKEH8P12NsrLQ", "http://purl.org/np/RADV-A9tz31I_WDowcxskTtP46g3wmVkvX84LrT76f7ks", "http://purl.org/np/RAJQa1NSYYfEVGpXo5cKAla2iIXcQ1hZMA2DkYhgSjiX4", "http://purl.org/np/RAKw71EWR6jMBVqvVKChG-b84OJfubfYDYgIl470SXb5c", "http://purl.org/np/RAx-dStvlLMg_209EsxfNK6PwwC-TC5RYcTWgMzR8TcBo", "http://purl.org/np/RAo585DeNjWreSUUCn2vulkCfQr4h3DbB4XIta84rmfPU", "http://purl.org/np/RA4B56P2xxfpUrjooCsvTGL1vRSXAMYckr4seakzzRX8o", "http://purl.org/np/RA7r_9VtKjxnKqXLnY4QKwy7wBPw7NRvDnSsIbF5eo25M", "http://purl.org/np/RAg51Xu-TVqV6F04XrVtu0TkfAzlpHOtPDt73JhE7dzmI", "http://purl.org/np/RAyRC-4BXJpJHRSvehauXP_K0ysjZBoUvByJ7DoBiNxBA", "http://purl.org/np/RA-Q8OR6_xjIlVC0A0Z8oz1L-rktMyTGunyUFlhPxj2ac", "http://purl.org/np/RA8FelCvPBxTggV1kWoWeWpAxMHigoTMJwbaz9-O2_B-g", "http://purl.org/np/RAFjdyQuwxeqlMJUlmIWak3VI0FlKdCEFLvNvO_t2QCzg", "http://purl.org/np/RAJ_wIH5Q8hc-PhR4wSLNcXLgaWO6Kp5wHrKZhkyOPn84", "http://purl.org/np/RAS1KDqZfjLZreSOLxLuTefqgn2vckFNleWuDEk5dEiWI", "http://purl.org/np/RA5Olx74ux0TvO3-hwaD1vPhl3Woqm9zrn6DkbhRPQS9g", "http://purl.org/np/RAeHcB7r8BQv8xU6yiv7xhwACbwdoW1RjK4WKbC8ZOw38", "http://purl.org/np/RAD1pxbJwAod7VFBAeiRP4iVc0uV3_RoIKTEv5L4AdboM", "http://purl.org/np/RAtHGR5Kj0bL13RFgRqCF9iYxYpXA5uvu5rpaWxbDP5t4", "http://purl.org/np/RAne7JRdrExd2cwSR-EmN5ngIp0WpCoKnGSfT6RGoA244", "http://purl.org/np/RALdAq2PVpaiqlUT098sFzQK8CwB7RZBMMeDkL-4ypX5A", "http://purl.org/np/RArM1xzQ5jGjq9NMeBLmUj5zr-CZSj71rWJ-ZurJHK880", "http://purl.org/np/RAOIaR2cbXfTG7YytjJj2YB1_AXgU2iCFBg5F-sbplyVs", "http://purl.org/np/RAvWo-W8W6ZHCcHshhDiWTeqGvygRZP1m1S9qRkeiFC_Q", "http://purl.org/np/RAbb6ql93HZxeGrLEsQTLfuPr_R_QinBkvD-ohh_9Etsg", "http://purl.org/np/RAV7Y1ysrdLU8x2I7Xg5H1EbAwhCNRov6veSHXGPWcjqU", "http://purl.org/np/RAJrXhdcuhGuwNwpaK8ZMc6E4dy4qak-y3zDZjiHAYlwA", "http://purl.org/np/RA5ZUzQ-tMjYUW3nXZQAzkVfsHF-C0l9KRhY-ZPoyG8Pk", "http://purl.org/np/RAMPlFJkJ_Ay0ovNx0rrJCbZod3DodODOmARn6_6iZ6OU", "http://purl.org/np/RAcOBsOMkk4DDy4pdu4RsiTOvHv-RTjMEX-DdDJU2gAWA", "http://purl.org/np/RAeBQim7z468T0IIIkVeKSldz5ELhl0fO9-LSfSQemtcE", "http://purl.org/np/RAxlj-kxgxbu94cNeMumvG0pZMoUKcaLF1vTrXVMRJBn4", "http://purl.org/np/RAoXzNG5fxEiJL0zTybUvpE-O8278Mctzuhmr0ZCa1m0Y", "http://purl.org/np/RAD7jBxO43gUrKI_a1u6tjqhTmRgnQzjdnmcUQAwuuS9c", "http://purl.org/np/RAbYiwrLGYxYZX4Dx0jPpM27LyXtb2CaYqGcpHCD7Yu6s", "http://purl.org/np/RA4KqDeGAYZD3R-3zd-KnfR5IfkLR_ZzR2FJXej1DAglM", "http://purl.org/np/RAyWQowbnmUC65Bp2sd5ChFkM7o-3hCuGLIuR69z78Qg4", "http://purl.org/np/RAxXQosfQmj4gCWJNYVF86UeEm5F937fGvrI-WoU0Na9k", "http://purl.org/np/RAvMD5tVgJfuOOwRU5hg1Ebt91q0gMI6VrqL43ttA2M34", "http://purl.org/np/RAa3GelC58tD-1WJmbrEdgncGURfYwhiAKuAYWT4f9vZw", "http://purl.org/np/RARSaEYpWIYla2OEaofNrSwAtuxQG9ncJEnBzPBM0e2to", "http://purl.org/np/RAe0cxQ7BcYcYptlibeIBWIo7JXbPSkOMZ-shmyrgH38I", "http://purl.org/np/RAtNHQO4xuN9_NH1JTCwarhFV5Rd4D2f5FbfOZachJWd0", "http://purl.org/np/RAf77Ce34uUIamj_fn4ejO3mVs4PSdA_JWt_aClA94e0k", "http://purl.org/np/RAibQ9QGJxhBouSEaf50L-tnpND9CB2VCRTOls_7W9ack", "http://purl.org/np/RAAwl-RZMcLYiE6kpE5rJsvqr8sU2M0gcvV--CwWsRpRc", "http://purl.org/np/RAcbqCvGgymJONvYOjYS1FXPCYMkDu3OYMlg2fHHdWPP4", "http://purl.org/np/RAUh9JgBwmv1pe0_GTCrJ1M5ocmBbEDmdxMf-nwcUAUXU", "http://purl.org/np/RA9rvr_NRBZXk4CX6HQ8RLBMZLlVNR4J2mjVwN9-IFmag", "http://purl.org/np/RAlekmwVrsLBn6AM15VWKa49sttCkxbuamzHyOtHJXJcI"]

print(f'🛎️  {str(len(np_list))} drug indications has been processed')

np_index = np_client.create_nanopub_index(
    np_list, 
    title="Off-label drug indications dataset", 
    description="""A dataset of 327 off-label drug indications found in PubMed articles. With additional information on the context of the indications, such as the target group age range (adult/children), or if the target group has a specific phenotype. 
Drugs are identified by their DrugBank IDs, and conditions are identified by their MONDO, EFO, or HPO IDs.
Curated by Ricardo de Miranda Azevedo. See https://github.com/MaastrichtU-IDS/off-label-drug-indications-dataset for more details.""", 
    see_also="https://github.com/MaastrichtU-IDS/off-label-drug-indications-dataset",
    creators=[CREATOR_ORCID], 
    creation_time="2021-10-02T00:00:00"
)

if args.publish:
    index_uri = np_client.publish(np_index)
else:
    print(np_index._rdf.serialize(format='trig'))
    index_uri = np_client.sign(np_index)

print('✅ Published Nanopub Index:')
print(index_uri)