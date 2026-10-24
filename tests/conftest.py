import gzip

import pytest

# Four releases that break naive parsers:
#  1 has track-level artists nested inside <tracklist> (must NOT become release credits)
#  2 has a forbidden control byte (\x0b) in its title and "?" as its date
#  3 has a zeroed month and day, and is the main release of a master
#  4 has an id that isn't a number (must be quarantined, not crash the run)
NASTY_RELEASES = b"""<releases>
<release id="101" status="Accepted">
  <artists><artist><id>9001</id><name>Seven Lions</name><anv></anv><join>&amp;</join><role></role></artist>
           <artist><id>9002</id><name>Illenium</name><anv></anv><join></join><role></role></artist></artists>
  <title>Example Collab</title>
  <labels><label name="Ophelia Records" catno="OPH001" id="501"/></labels>
  <extraartists><artist><id>9100</id><name>Some Engineer</name><role>Mastered By</role></artist></extraartists>
  <formats><format name="File" qty="1"><descriptions><description>MP3</description></descriptions></format></formats>
  <genres><genre>Electronic</genre></genres>
  <styles><style>Dubstep</style><style>Future Bass</style></styles>
  <country>US</country>
  <released>2019-03-15</released>
  <data_quality>Correct</data_quality>
  <tracklist>
    <track><position>1</position><title>Intro</title><duration>3:30</duration>
      <artists><artist><id>9999</id><name>Track Only Guest</name></artist></artists></track>
    <track><position>2</position><title>Drop</title><duration>4:10</duration></track>
  </tracklist>
</release>
<release id="102" status="Accepted">
  <artists><artist><id>9003</id><name>Virtual Riot</name></artist></artists>
  <title>Broken\x0bTitle</title>
  <released>?</released>
  <styles><style>Dubstep</style></styles>
</release>
<release id="103" status="Accepted">
  <artists><artist><id>9004</id><name>Said The Sky</name></artist></artists>
  <title>Zeroes</title>
  <released>2012-00-00</released>
  <master_id is_main_release="true">7001</master_id>
</release>
<release id="not-a-number" status="Accepted">
  <title>Bad Id</title>
</release>
</releases>
"""

NASTY_LABELS = b"""<labels>
<label><id>501</id><name>Ophelia Records</name>
  <sublabels><label id="601">Ophelia Sub</label><label id="602">Another Sub</label></sublabels></label>
<label><id>601</id><name>Ophelia Sub</name><parentLabel id="501">Ophelia Records</parentLabel></label>
</labels>
"""


@pytest.fixture
def nasty_releases(tmp_path):
    path = tmp_path / "discogs_20261001_releases.xml.gz"
    with gzip.open(path, "wb") as fh:
        fh.write(NASTY_RELEASES)
    return path


@pytest.fixture
def nasty_labels(tmp_path):
    path = tmp_path / "labels.xml"
    path.write_bytes(NASTY_LABELS)
    return path
