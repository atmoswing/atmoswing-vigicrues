# Changelog AtmoSwing-vigicrues


## Non publié

### Ajouts

*   Pré-action `DownloadEcmwfData` : téléchargement des prédicteurs du CEP depuis les données ouvertes ECMWF (`ecmwf-opendata`), en remplacement du dépôt SFTP. Les champs GRIB2 sont découpés sur le domaine, sans conversion (AtmoSwing lisant les fichiers du CEP en GRIB2 requis), avec reprise des téléchargements interrompus.
*   Options `proxy_type` (`http`, `socks4`, `socks5`), `proxy_username` et `proxy_password` pour les transferts SFTP et FTP.
*   Option `known_hosts` pour vérifier la clé du serveur SFTP (recommandé).
*   Option `timeout` pour le téléchargement des données GFS.
*   Dépendances optionnelles via `pip install atmoswing-vigicrues[grib]`.

### Changements

*   Codes de retour : -1 si les pré-actions échouent pour toutes les dates tentées (AtmoSwing n'est plus lancé), 1 si une post-action ou une dissémination échoue.
*   Messages émis via `logging`, avec horodatage et niveau.
*   Configuration chargée avec `yaml.safe_load`.
*   Récupération SFTP : décompression des fichiers `.gz` seuls et extraction sécurisée des archives tar.
*   Python 3.9 ou supérieur requis.
*   Image Docker de base épinglée par digest et vérifiée avant publication.
*   CI : flake8 bloquant, tests de Python 3.9 à 3.13, publication PyPI par « trusted publishing ».

### Corrections

*   Les dépendances du paquet n'étaient pas installées depuis PyPI.
*   Image Docker : le module n'était pas installé et les transformations GRIB ne pouvaient décoder aucun fichier.
*   Les erreurs de configuration et les dates mal formatées sont signalées par un message explicite.
*   `python -m atmoswing_vigicrues` transmet le code de retour au système.
*   Proxys : le transfert FTP ne détourne plus toutes les connexions du processus, la récupération SFTP passe réellement par le proxy HTTP, et les proxys vides de `DownloadGfsData` sont ignorés.
*   Transferts SFTP/FTP : connexions fermées, échecs signalés sans exception, répertoire FTP vide accepté.
*   Diffusion : les exports JSON en erreur sont remplacés sur le serveur distant, et une diffusion sans fichier n'est plus un échec.
*   Export BdApBp : les fichiers en erreur sont régénérés et les codes d'erreur 100 et 110 sont conservés.
*   Export PRV : les fichiers netCDF sont toujours fermés.
*   Dates MJD infra-journalières erronées.
*   Erreurs d'AtmoSwing Forecaster signalées deux fois.
*   `TransformEcmwfData` s'affichait comme « Transformation données GFS ».
*   Les transformations GRIB signalent l'absence d'`atmoswing-toolbox` dès leur création.


## v1.2.0 - 11 Avril 2025

### Corrections

*   Correction du support des proxys HTTP dans le téléversement SFTP.


## v1.1.9 - 11 Avril 2025

### Changements

*   Amélioration du support des proxys HTTP dans le téléversement SFTP.


## v1.1.8 - 28 Mars 2025

### Changements

*   Dissémination FTP: si le fichier est déjà présent, il n'est pas écrasé.


## v1.1.7 - 27 Mars 2025

### Ajouts

*   Ajout d'une dissémination des résultats par FTP.


## v1.1.6 - 04 Août 2023

### Ajouts

*   Ajout d'une option en ligne de commande pour spécifier l'intervalle de temps.
*   Ajout de 'time_increment' et 'time_step_back' comme options de DownloadGfsData.


## v1.1.5 - 02 Juillet 2023

### Corrections

*   Conversion du format des dates dans les exports pour assurer la compatibilité.
*   Correction d'un problème avec la transformation des fichiers grib du CEP.


## v1.1.4 - 08 Juin 2023

### Changements

*   Ajout de messages sur les téléchargements GFS.

### Corrections

*   Correction de problèmes avec le rapatriement SFTP.


## v1.1.3 - 20 Mai 2023

### Changements

*   Mise à jour de l'image d'AtmoSwing Forecaster.


## v1.1.2 - 16 Mai 2023

### Corrections

*   Retour négatif si des fichiers ne sont pas disponibles pour l'heure donnée sur le serveur SFTP.


## v1.1.1 - 15 Mai 2023

### Ajouts

*   Ajout du nombre de fichiers récupérés par SFTP.
*   Ajout de l'affichage du contenu du journal du Forecaster en cas d'erreur.

### Changements

*   Exécute toujours les post-actions et contrôle si les fichiers cibles existent avant
    de les écraser


## v1.1.0 - 12 Mai 2023

### Ajouts

*   Ajout de la version courte des arguments.
*   Ajout de l'option only_relevant_stations dans le fichier json généré.
*   Ajout de l'option de formatage de la date pour l'export PRV.
*   Option pour spécifier les variables du rapatriement SFTP.
*   Option pour sauter l'action AtmoSwing Forecaster.
*   Ajout de tests

### Changements

*   Le flux de prévision continue même si les pré-actions ont échoué.
*   La prévision s'arrête si le AtmoSwing Forecaster échoue.
*   Si des fichiers sont déjà présents, la connexion SFTP n'est pas créée.
*   Les post-actions ne sont effectuées que si de nouveaux fichiers sont disponibles.
*   Mise à jour des actions transformant les fichiers grib.

### Corrections

*   Mise à jour de l'utilisation de Paramiko.
*   Correction de variables GFS manquantes.
*   Correction de problèmes de style de code.


## v1.0.4 - 10 Mai 2023

### Ajouts

*   Ajouts de messages pour renseigner sur le succès (ou non) après l'exécution d'une action.
*   Ajouts du nom de l'action (selon le fichier de configuration) dans les messages.
*   La plage temporelle dans laquelle les fichiers des modèles météo sont cherchés peut être spécifié par pré-action.

### Changements

*   Les post-actions échouent lorsqu'il n'y a pas de fichier disponible
*   Le flux de la prévision est arrêté lorsqu'une pré-action échoue.


## v1.0.3 - 08 Mai 2023

### Changements

*   Mise à jour de l'image d'AtmoSwing Forecaster.


## v1.0.2 - 05 Mai 2023

### Corrections

*   Support de caractères spéciaux dans les fichiers de config (p.ex. mots de passe).


## v1.0.1 - 18 Avril 2023

### Ajouts

*   Ajout de tags aux conteneurs Dockers.

### Corrections

*   Correction du nom des fichiers GFS téléchargés.
*   Ajout d'un retour positif après téléchargement des données par SFTP.


## v1.0.0 - 17 Avril 2023

Release initiale.
