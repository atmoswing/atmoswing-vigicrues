Introduction
============

Module Python pour l'intégration d'AtmoSwing dans le réseau Vigicrues.


|github| |pypi| |docker| |python|

.. |github| image:: https://img.shields.io/github/v/release/atmoswing/atmoswing-vigicrues
    :target: https://github.com/atmoswing/atmoswing-vigicrues
.. |pypi| image:: https://img.shields.io/pypi/v/atmoswing-vigicrues
   :target: https://pypi.org/project/atmoswing-vigicrues/
.. |docker| image:: https://img.shields.io/docker/v/atmoswing/atmoswing-vigicrues?label=docker
   :target: https://hub.docker.com/r/atmoswing/atmoswing-vigicrues
.. |python| image:: https://img.shields.io/badge/python-min_3.7-green
   :target: https://www.python.org/

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
* Le module atmoswing-vigicrues (``pip install atmoswing-vigicrues`` ou l'image docker ``docker pull atmoswing/atmoswing-vigicrues``)

Utilisation
-----------

Le paquet est constitué de plusieurs modules qui peuvent être activés et configurés dans un fichier de configuration. Plusieurs flux de prévision peuvent être configurés sur un serveur / PC par la création de différents fichiers de configuration. Il n’y a pas de paramètres codés en dur dans le code. L’exécution d’un flux de prévision est effectuée par la commande :

.. code-block:: bash

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

Exemple de fichier de configuration
-----------------------------------

Un exemple de fichier de configuration est présenté ci-dessous :

.. code-block:: yaml

    atmoswing:
      name: Forecast now
      with:
        atmoswing_path: 'C:\Program Files\AtmoSwing\atmoswing-forecaster.exe'
        batch_file: 'files/batch_file.xml'
        output_dir: 'D:\atmoswing\forecasts'
        target: 'now'
        proxy: ''
        proxy_user: ''

    pre_actions:
      - name: Download GFS data (Z)
        uses: DownloadGfsData
        active: True
        with:
          output_dir: 'D:\atmoswing\gfs'
          lead_time_max: 168
          variables: ['hgt']
          levels: [500, 1000]
          domain: [-20, 30, 25, 65]
          resolution: 0.5
          max_attempts: 8
          proxies:
            http: ''
            https: ''

    post_actions:
      - name: Export BdApBp
        uses: ExportBdApBp
        active: True
        with:
          output_dir: 'D:\atmoswing\exports\bdapbp'
          number_analogs: 10
          only_relevant_stations: True

      - name: Export PRV for Scores
        uses: ExportPrv
        enable: True
        with:
          output_dir: 'D:\atmoswing\exports\prv'
          frequencies: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]

    disseminations:
      - name: Transfer SFTP netcdf
        uses: TransferSftpOut
        active: True
        with:
          local_dir: 'D:\atmoswing\forecasts'
          extension: '.nc'
          hostname: '127.0.0.1'
          port: 4422
          username: 'foo'
          password: 'pass'
          proxy_host: ''
          proxy_port: ''
          remote_dir: 'upload/netcdf'

      - name: Transfer SFTP prv
        uses: TransferSftpOut
        active: True
        with:
          local_dir: 'D:\atmoswing\exports'
          extension: '.json'
          hostname: '127.0.0.1'
          port: 4422
          username: 'foo'
          password: 'pass'
          proxy_host: ''
          proxy_port: ''
          remote_dir: 'upload/json'

      - name: Transfer SFTP prv
        uses: TransferSftpOut
        active: True
        with:
          local_dir: 'D:\atmoswing\exports'
          extension: '.csv'
          hostname: '127.0.0.1'
          port: 4422
          username: 'foo'
          password: 'pass'
          proxy_host: ''
          proxy_port: ''
          remote_dir: 'upload/prv'

La partie « Composants » de la documentation fournit le détail des paramètres de chaque action.

Structure
---------

Le schéma ci-dessous présente la structure des classes principales du module.

.. currentmodule:: atmoswing_vigicrues
.. inheritance-diagram:: Controller PreAction TransferSftpIn DownloadGfsData TransformGfsData TransformEcmwfData PostAction ExportBdApBp ExportPrv Dissemination TransferSftpOut
   :parts: 1

