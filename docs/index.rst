`idiosync` - User database synchronizer
=======================================

Enterprise Single Sign-On (SSO) allows an organisation to maintain a
single centralised database of users.  Each user can then log in to
all of the organisation's services using the same username and
password.

For example: a user may first attempt to access an internal wiki page.
The user is redirected to the authentication server, where she enters
her username and password, and is then redirected back to view the
wiki page.  The user subsequently attempts to access a webmail server,
which recognises the existing authentication and allows immediate
access to the mailbox without a second password prompt.

Overview
--------

``idiosync`` can be used to synchronize user and group definitions
from a central user database (such as FreeIPA_ or `Active
Directory`_) into the databases used by individual applications (such
as MediaWiki_ or `Request Tracker`_).  ``idiosync`` ensures that
changes in the central user database are immediately reflected into
the individual application databases.  For example:

- When a new user is created in the central user database, a
  corresponding user will automatically be created in the application
  user database.

- When a user is renamed in the central user database, the
  corresponding user in the application database will automatically be
  renamed.

- When a user is added to a group in the central user database, the
  corresponding user in the application database will automatically be
  added to the corresponding group.

- When a user is disabled in the central user database, the
  corresponding user in the application database will automatically be
  disabled.

All of these changes are reflected immediately.  Unlike other
synchronization mechanism, ``idiosync`` does not delay changes until
the user next logs in to the application.

Authentication
--------------

``idiosync`` is intended to work in conjunction with an authentication
mechanism such as Kerberos_, SAML_, or `OpenID Connect`_.
``idiosync`` is solely responsible for ensuring that the application
database includes correct definitions for all of the relevant users
and groups, and the authentication mechanism is solely responsible for
verifying the users' credentials.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules/idiosync

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Active Directory: https://wikipedia.org/wiki/Active_Directory
.. _FreeIPA: https://www.freeipa.org
.. _Kerberos: https://web.mit.edu/kerberos/
.. _MediaWiki: https://www.mediawiki.org/
.. _OpenID Connect: https://openid.net/connect/
.. _Request Tracker: https://bestpractical.com/request-tracker
.. _SAML: https://en.wikipedia.org/wiki/Security_Assertion_Markup_Language
