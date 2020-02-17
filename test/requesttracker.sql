--
-- Request Tracker test database schema
--

CREATE TABLE `Principals` (
  `id` INTEGER PRIMARY KEY NOT NULL,
  `PrincipalType` varchar(16) NOT NULL,
  `Disabled` smallint(6) NOT NULL DEFAULT 0
);

CREATE TABLE `Users` (
  `id` INTEGER PRIMARY KEY NOT NULL,
  `Name` varchar(200) NOT NULL,
  `Password` varchar(256) DEFAULT NULL,
  `AuthToken` varchar(16) DEFAULT NULL,
  `Comments` text DEFAULT NULL,
  `Signature` text DEFAULT NULL,
  `EmailAddress` varchar(120) DEFAULT NULL,
  `FreeformContactInfo` text DEFAULT NULL,
  `Organization` varchar(200) DEFAULT NULL,
  `RealName` varchar(120) DEFAULT NULL,
  `NickName` varchar(16) DEFAULT NULL,
  `Lang` varchar(16) DEFAULT NULL,
  `Gecos` varchar(16) DEFAULT NULL,
  `HomePhone` varchar(30) DEFAULT NULL,
  `WorkPhone` varchar(30) DEFAULT NULL,
  `MobilePhone` varchar(30) DEFAULT NULL,
  `PagerPhone` varchar(30) DEFAULT NULL,
  `Address1` varchar(200) DEFAULT NULL,
  `Address2` varchar(200) DEFAULT NULL,
  `City` varchar(100) DEFAULT NULL,
  `State` varchar(100) DEFAULT NULL,
  `Zip` varchar(16) DEFAULT NULL,
  `Country` varchar(50) DEFAULT NULL,
  `Timezone` varchar(50) DEFAULT NULL,
  `SMIMECertificate` text DEFAULT NULL,
  `Creator` int(11) NOT NULL DEFAULT 0,
  `Created` datetime DEFAULT NULL,
  `LastUpdatedBy` int(11) NOT NULL DEFAULT 0,
  `LastUpdated` datetime DEFAULT NULL,
  UNIQUE (`Name`)
);

CREATE TABLE `Groups` (
  `id` INTEGER PRIMARY KEY NOT NULL,
  `Name` varchar(200) DEFAULT NULL,
  `Description` varchar(255) DEFAULT NULL,
  `Domain` varchar(64) DEFAULT NULL,
  `Instance` int(11) DEFAULT NULL,
  `Creator` int(11) NOT NULL DEFAULT 0,
  `Created` datetime DEFAULT NULL,
  `LastUpdatedBy` int(11) NOT NULL DEFAULT 0,
  `LastUpdated` datetime DEFAULT NULL
);

CREATE TABLE `GroupMembers` (
  `id` INTEGER PRIMARY KEY NOT NULL,
  `GroupId` int(11) NOT NULL DEFAULT 0,
  `MemberId` int(11) NOT NULL DEFAULT 0,
  `Creator` int(11) NOT NULL DEFAULT 0,
  `Created` datetime DEFAULT NULL,
  `LastUpdatedBy` int(11) NOT NULL DEFAULT 0,
  `LastUpdated` datetime DEFAULT NULL,
  UNIQUE (`GroupId`,`MemberId`)
);
