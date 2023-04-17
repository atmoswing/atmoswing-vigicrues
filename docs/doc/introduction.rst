Introduction
============

Module Python pour l'intégration d'AtmoSwing dans le réseau Vigicrues.


Objectif
--------

Le module a pour but la gestion du flux de la prévision par AtmoSwing. Il permet :

* de télécharger les fichiers de sortie de modèles météo (p. ex. GFS),
* de transformer de tels fichiers en un format netCDF générique,
* d'exécuter les prévisions par AtmoSwing,
* d'extraire les résultats en d'autres formats (p.ex. json),
* et de diffuser ces fichiers par SFTP.


Installation
------------

Pour utiliser le module atmoswing-vigicrues, il faut installer :

* Python >= 3.7
* AtmoSwing Forecaster (de préférence la version serveur)
* Le module atmoswing-vigicrues ("``pip install atmoswing-vigicrues``" ou l'image docker "``docker pull atmoswing/atmoswing-vigicrues``")

Utilisation
-----------

Le paquet est constitué de plusieurs modules qui peuvent être activés et configurés dans un fichier de configuration. Plusieurs flux de prévision peuvent être configurés sur un serveur / PC par la création de différents fichiers de configuration. Il n’y a pas de paramètres codés en dur dans le code. L’exécution d’un flux de prévision est effectuée par la commande :
python -m atmoswing_vigicrues --config-file="chemin/vers/fichier/config.yaml"
Le fichier de configuration définit :

* Les propriétés de la prévision par AtmoSwing
* Les pré-actions : les actions à effectuer préalablement à la prévision par AtmoSwing
* Les post-actions : les actions à effectuer après la prévision par AtmoSwing
* Les disséminations : les actions de transfert des résultats

Le flux de la prévision est le suivant :

1. pré-actions
2. prévision par AtmoSwing
3. post-actions
4. diffusion

La partie « Composants » de la documentation fournit le détail des paramètres de chaque action.
