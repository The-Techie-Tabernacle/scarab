CREATE TABLE IF NOT EXISTS "Region"
(
"ID" integer primary key autoincrement not null ,
"Name" varchar ,
"NumNations" integer ,
"Delegate" varchar ,
"DelegateVotes" integer ,
"DelegateAuth" integer ,
"Founder" varchar ,
"FounderAuth" integer ,
"Factbook" varchar ,
"Embassies" varchar ,
"LastUpdate" float ,
"LastMajorUpdate" float ,
"LastMinorUpdate" float ,
"hasPassword" integer ,
"hasGovernor" integer
);
CREATE TABLE IF NOT EXISTS "Nation"
(
"ID" integer ,
"Name" varchar ,
"Region" integer
);
CREATE VIEW IF NOT EXISTS UpdateData AS
SELECT
NumNations,
MajorLength,
MajorLength / NumNations AS TPN_Major,
MinorLength,
MinorLength / NumNations AS TPN_Minor
FROM ud_1;

CREATE TABLE IF NOT EXISTS "Updaters"
(
"updaterID" integer,
"org" varchar,
"rank" varchar,
"nation" varchar,
"handle" varchar,
"isVerified" integer,
"discord" varchar
);
CREATE TABLE IF NOT EXISTS "Tag"
(
"tagID" integer,
"date" integer,
"isMajor" integer,
"WFE" varchar,
"bannerPath" varchar,
"flagPath" varchar
);
CREATE TABLE IF NOT EXISTS "Hits"
(
"tagID" integer,
"point" integer,
"region" integer,
);
CREATE VIEW IF NOT EXISTS tagRecords AS
SELECT
    Updaters.Nation,
    (SELECT Name FROM Region WHERE ID = Hits.region) AS Target,
    (SELECT date FROM Tag WHERE tagID = Hits.tagID) AS date
FROM Hits
INNER JOIN Updaters ON Hits.point = Updaters.updaterID;