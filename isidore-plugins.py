# -*- coding: utf-8 -*- 
#
#    Copyright 2013 Pierre-Amiel Giraud
#    
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
from SPARQLWrapper import SPARQLWrapper
from urllib import urlretrieve
import codecs
from filecmp import cmp
from sys import exit
from os import rename
import logging
logging.basicConfig(filename='isidore-opensearch.log',level=logging.DEBUG,format='%(asctime)s %(message)s')
sparql = SPARQLWrapper("http://www.rechercheisidore.fr/sparql")
#Étape 1 : faut-il faire une mise-à-jour? Après avoir vérifié si le script a déjà été
#lancé, on regarde si la liste des collections a changé depuis la dernière vérification.
#Si oui, il faut passer à l'étape 2.
def liste_collec(maj = True):
	if maj is True:
		maj = "_maj"
	else:
		maj = ""
	return urlretrieve("http://www.rechercheisidore.fr/sparql?default-graph-uri=&query=SELECT+%3Fs%0D%0AWHERE+{+%3Fs+rdf%3Atype+%3Chttp%3A%2F%2Fwww.rechercheisidore.fr%2Fclass%2FCollection%3E+}&format=application%2Frdf%2Bxml&timeout=5000&debug=off", "liste_collec" + maj + ".xml")
try:
	with open('liste_collec.xml') as file:
		logging.info('Lancement du script. La liste des collections existe bien.')
		liste_collec()
		if cmp('liste_collec.xml', 'liste_collec_maj.xml'):
			logging.info('Isidore moissonne toujours les mêmes collections. Arrêt du script.')
			exit()
		else:
			logging.info('Isidore ne moissonne plus les mêmes collections. Mise à jour nécessaire.')
			rename('liste_collec_maj.xml', 'liste_collec.xml')
except IOError as e:
	liste_collec(maj = False)
	logging.info('Premier lancement du script. Création de la liste des collections et du fichier de logs.')
#Étape 2 : Le cas échéant, on récupère la description des collections et on génère
#à la fois les fichiers OpenSearch et la page pour pouvoir les récupérer.
#
#Étape 2a : récupération
sparql.setQuery("""
	PREFIX dcterms: <http://purl.org/dc/terms/>
	PREFIX foaf: <http://xmlns.com/foaf/0.1/>
	SELECT ?uricollection ?titrecollection ?description ?adresseweb ?logo WHERE {
		?uricollection ?predicat <http://www.rechercheisidore.fr/class/Collection>.
		?uricollection dcterms:title ?titrecollection. ?uricollection dcterms:description ?description.
		?uricollection foaf:homepage ?adresseweb.
		?uricollection foaf:logo ?logo.
	}
	ORDER BY ASC(?titrecollection)
	LIMIT 300""")
collections = sparql.query().convert().toxml()
xml = codecs.open('collections.xml','w+', 'utf-8')
print>>xml,collections
xml.close()
#Étape 2b : génération des fichiers opensearch et de la page HTML
import xml.etree.ElementTree as ET
tree = ET.parse('collections.xml')
root = tree.getroot()
header = codecs.open('header.html', 'r', 'utf-8').read()
html = codecs.open('docs/index.html','w+', 'utf-8')
print>>html,header
index = []
for resultat in root[1]:
	uri = resultat[0][0].text
	titre = resultat[1][0].text
	description = resultat[2][0].text
	if not description:
		description = "Aucune description disponible."
	else:
		description = description.replace('&','&amp;')
#Code temporaire, tant que le bug de Virtuoso n'est pas résolu sur Isidore.
#	titre = titre.encode('latin-1').decode('utf_8')
#	description = description.encode('latin-1').decode('utf_8')
#Fin du code temporaire
	adresse = resultat[3][0].text
	logo = resultat[4][0].text
	os_shortname = titre[0:16] + "via ISIDORE"
	os_description = titre
	os_codename = uri[-14:]
	os_filename = os_codename.replace("/", "").replace(".","") + '.xml'
	os = """<?xml version="1.0" encoding="UTF-8"?>
<SearchPlugin xmlns="http://www.mozilla.org/2006/browser/search/"  xmlns:os="http://a9.com/-/spec/opensearch/1.1/">
<os:ShortName>""" + os_shortname + """</os:ShortName>
<os:Description>""" + os_description + """</os:Description>
<os:InputEncoding>UTF-8</os:InputEncoding>
<os:Image height="16" width="16" type="image/x-icon">http://www.rechercheisidore.fr/favicon.ico</os:Image>
<os:Url type="text/html" method="GET" template="http://www.rechercheisidore.fr/search?q={searchTerms}&amp;collection=""" + os_codename + """"></os:Url>
<os:Url type="application/x-suggestions+json" method="GET" template="http://www.rechercheisidore.fr/suggest/?q={searchTerms}"></os:Url>
<SearchForm>http://www.rechercheisidore.fr/search?collection=""" + os_codename + """</SearchForm>
<os:Url type="application/opensearchdescription+xml"
     rel="self"
     template="http://www.insolit.org/isidore-opensearch/""" + os_filename + """" />
</SearchPlugin>"""
	fich = codecs.open('docs/' + os_filename,'w+', 'utf-8')
	print>>fich,os
	fich.close()
	initiale = titre[0].encode('utf-8')
	if not index:
		index.append(initiale)
		ancre = "<a class =\"ancre\" name=\"%s\"></a>" % (initiale,)
#		ancre = " id=\"%s\" " % (initiale,)
	elif index[-1] is not initiale:
		index.append(initiale)
		ancre = "<a class =\"ancre\" name=\"%s\"></a>" % (initiale,)
#		ancre = " id=\"%s\"" % (initiale,)
	else:
		ancre = ""
	title = ancre + "<h1>" + titre + "</h1>\n"
#	title = "<h1%s>%s</h1>\n" % (ancre,titre)
	description = "<li class=\"description\">" + description + "</li>\n"
	lien = "<li class=\"lien_os\"><button onclick=\"javascript:window.external.AddSearchProvider('http://www.insolit.org/isidore/" + os_filename + "')\" type=\"button\">Installez le plugin de recherche " + os_shortname + "</button></li>\n"
	logo = "<li class=\"logo\"><img alt=\"Image indisponible\" src=\"" + logo + "\" /></li>\n"
	collec = "<div class=\"collec\">" + title + "<ul>" + description + lien + logo + "</ul></div><hr />"
	print>>html,collec
print>>html,"<div id=\"nav\"><ul>"
for i in index:
	lettre = "<li><a href=\"#" + i + "\">" + i + "</a></li>"
	print>>html,lettre
print>>html,"</ul></div>\n"
footer = codecs.open('footer.html', 'r', 'utf-8').read()
print>>html,footer
html.close()
logging.info('Génération réussie des plugins et de la page HTML.')
