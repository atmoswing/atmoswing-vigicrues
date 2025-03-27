Composants
==========

.. currentmodule:: atmoswing_vigicrues

Controller
----------

.. autoclass:: Controller
   :members:
   :undoc-members:
   :show-inheritance:


Pre-actions
-----------

.. inheritance-diagram:: PreAction TransferSftpIn DownloadGfsData TransformGfsData TransformEcmwfData
   :parts: 1


Classe de base des pré-actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: PreAction
   :members:
   :undoc-members:
   :show-inheritance:

Transfert SFTP
~~~~~~~~~~~~~~

.. autoclass:: TransferSftpIn
   :members:
   :undoc-members:
   :show-inheritance:

Téléchargement GFS
~~~~~~~~~~~~~~~~~~

.. autoclass:: DownloadGfsData
   :members:
   :undoc-members:
   :show-inheritance:

Transformation données GFS
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: TransformGfsData
   :members:
   :undoc-members:
   :show-inheritance:

Transformation données CEP
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: TransformEcmwfData
   :members:
   :undoc-members:
   :show-inheritance:


Post-actions
------------

.. inheritance-diagram:: PostAction ExportBdApBp ExportPrv
   :parts: 1

Classe de base des post-actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: PostAction
   :members:
   :undoc-members:
   :show-inheritance:

Export BdApBp
~~~~~~~~~~~~~

.. autoclass:: ExportBdApBp
   :members:
   :undoc-members:
   :show-inheritance:

Export PRV
~~~~~~~~~~

.. autoclass:: ExportPrv
   :members:
   :undoc-members:
   :show-inheritance:


Dissemination
-------------

.. inheritance-diagram:: Dissemination TransferSftpOut
   :parts: 1

Classe de base des disséminations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: Dissemination
   :members:
   :undoc-members:
   :show-inheritance:

Transfert SFTP
~~~~~~~~~~~~~~

.. autoclass:: TransferSftpOut
   :members:
   :undoc-members:
   :show-inheritance:

Transfert FTP
~~~~~~~~~~~~~~

.. autoclass:: TransferFtpOut
   :members:
   :undoc-members:
   :show-inheritance:
