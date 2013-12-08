import datetime, os, sys, time, re, locale, ConfigParser
from string import Template

# Series agent name
SERIES_AGENT_NAME = 'Extended Personal Media Shows'

FILE_NAME_WITHOUT_EXT_REGEX = r'^(?P<fileWithoutExt>.*)\..+$'

def log(methodName, message, *args):
    Log(methodName + ' :: ' + message, *args)

# Only use unicode if it's supported, which it is on Windows and OS X,
# but not Linux. This allows things to work with non-ASCII characters
# without having to go through a bunch of work to ensure the Linux 
# filesystem is UTF-8 "clean".
#
def unicodize(s):
    filename = s
    
    log('unicodize', 'before unicodizing: %s', str(filename))
    if os.path.supports_unicode_filenames:
        try: filename = unicode(s.decode('utf-8'))
        except: pass
    log('unicodize', 'after unicodizing: %s', str(filename))
    return filename
      
class BaseMediaParser(object):
    '''
        Parses the file name and determines the type of tile that was found
    '''
    
    def setValues(self, match):
        # set the season summary
        self.seasonSummary = None
        if 'seasonTitle' in match.groupdict():
            self.seasonSummary = match.group('seasonTitle')
        
        # set the episode title
        self.episodeTitle = match.group('episodeTitle').strip()
        
        # set the episode summary
        self.episodeSummary = None
        # Get the summary file path
        # Find out what file format is being used
        match = re.search(FILE_NAME_WITHOUT_EXT_REGEX, self.mediaFile)
        if match:
            fileWithoutExt = match.group('fileWithoutExt').strip()
            log('setValues', 'file name without extension %s', fileWithoutExt)
            summaryFilePath = fileWithoutExt + '.summary'
            log('setValues', 'looking for summary file %s', summaryFilePath)
            # If the summary file exist read in the contents
            if os.path.exists(summaryFilePath) is True:
                log('setValues', 'summary file exists - reading contents')
                try:
                    summaryText = Core.storage.load(summaryFilePath, False)
                    self.episodeSummary = summaryText.replace('\n', '')
                except Exception as e:
                    log('setValues', 'error occurred reading contents of summary file %s : %s', summaryFilePath, e)
            else:
                log('setValues', 'summary file does not exist')


    def getSupportedRegexes(self):
        return []
    
    def containsMatch(self, mediaFile):
        retVal = False
        # Iterate over the list of regular expressions
        for regex in self.getSupportedRegexes():
            # Find out what file format is being used
            match = re.search(regex, mediaFile)
            if match:
                retVal = True
                break
            
        return retVal
        

    def parse(self, mediaFile, lang):
        self.mediaFile = mediaFile
        self.lang = lang

        # Iterate over the list of regular expressions
        for regex in self.getSupportedRegexes():
            # Find out what file format is being used
            match = re.search(regex, mediaFile)
            log('parse', 'regex %s - matches: %s', regex, match)
            if match:
                log('parse', 'found matches')
                self.setValues(match)
                break
  
    def getSeasonSummary(self):
        return self.seasonSummary

    def getEpisodeTitle(self):
        return self.episodeTitle

    def getEpisodeSummary(self):
        return self.episodeSummary

class SeriesDateBasedMediaParser(BaseMediaParser):

    def getSupportedRegexes(self):
        return [
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]{4})[-\. ]+(?P<seasonTitle>[^\\/]+)[\\/][^\\/]*(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' , #Show Title\2012 - Season Title\Show Title - 2012-09-19 - Episode Title.mp4, Show Title\2012 - Season Title\2012-09-19 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]{4})[\\/][^\\/]*(?P<episodeYear>[0-9]{4})[-\. ](?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' , #Show Title\2012\Show Title - 2012-09-19 - Episode Title.mp4, Show Title\2012\2012-09-19 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]{4})[-\. ]+(?P<seasonTitle>[^\\/]+)[\\/][^\\/]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' , #Show Title\2012 - Season Title\Show Title - 09-19-2013 - Episode Title.mp4, Show Title\2012 - Season Title\09-19-2013 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]{4})[\\/][^\\/]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[-\. ](?P<episodeYear>[0-9]{4})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' , #Show Title\2012\Show Title - 09-19-2013 - Episode Title.mp4, Show Title\2012\09-19-2013 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]{4})[-\. ]+(?P<seasonTitle>[^\\/]+)[\\/][^\\/]*(?P<episodeMonth>[0-9]{2})[-\. ](?P<episodeDay>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' #Show Title\2012\Show Title - 09-19 - Episode Title.mp4, Show Title\2012\09-19 - Episode Title.mp4
                ]
    
class SeriesEpisodeMediaParser(BaseMediaParser):
    
    def getSupportedRegexes(self):
        return [
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]+)[-\. ]+(?P<seasonTitle>[^\\/]+)[\\/][^\\/]*[eE](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$', #Show Title\2012 - Season Title\Show Title - s2012e09 - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]+)[\\/][^\\/]*[eE](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>.*)\.(?P<ext>.+)$' #Show Title\2012\Show Title - s2012e09 - Episode Title.mp4, Show Title\2012\e09 - Episode Title.mp4
                ] 
    
class SeriesSimpleMediaParser(BaseMediaParser):
    
    def getSupportedRegexes(self):
        return [
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonNumber>[0-9]+)[-\. ]+(?P<seasonTitle>[^\\/]+)[\\/](?P<episodeTitle>[^\\/]+)\.(?P<ext>.+)$', #Show Title\2006 - Season Title\Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonTitle>[^\\/]+)[\\/][^\\/]*[eE](?P<episodeNumber>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<episodeTitle>[^\\/]+)\.(?P<ext>.+)$', #Show Title\Season Title\exx - Episode Title.mp4
                r'(?P<showTitle>[^\\/]+)[\\/](?P<seasonTitle>[^\\/]+)[\\/](?P<episodeTitle>[^\\/]+)\.(?P<ext>.+)$' #Show Title\Season Title\Episode Title.mp4
                ] 

# List of series parsers
SERIES_PARSERS = [SeriesDateBasedMediaParser(), SeriesEpisodeMediaParser(), SeriesSimpleMediaParser()]

def Start():
    log('Start', 'starting agents %s, %s', SERIES_AGENT_NAME)
    pass

class ExtendedPersonalMediaAgentTVShows(Agent.TV_Shows):
    name = SERIES_AGENT_NAME
    languages = Locale.Language.All()
    accepts_from = ['com.plexapp.agents.localmedia']

    def search(self, results, media, lang):
        log('search', 'media id: %s', media.id)
        log('search', 'media file name: %s', str(media.filename))
        log('search', 'media primary metadata: %s', str(media.primary_metadata))
        log('search', 'media primary agent: %s', str(media.primary_agent))
        log('search', 'media title: %s', str(media.title))
        log('search', 'media show: %s', str(media.show))
        log('search', 'media name: %s', str(media.name))
        log('search', 'media season: %s', str(media.season))
        log('search', 'media episode: %s', str(media.episode))
        
        # Compute the GUID based on the media hash.
        try:
            part = media.items[0].parts[0]
            # Get the modification time to use as the year.
            filename = unicodize(part.file)
            log('search', 'part file name: %s', filename)
        except:
            log('search', 'part does not exist')
        
        results.Append(MetadataSearchResult(id=media.id, name=media.show, year=None, lang=lang, score=100))

    def update(self, metadata, media, lang):
        #test.test('Extended Personal Media - Scan')
        log('update', 'metadata: %s', str(metadata))
        log('update', 'media: %s', str(media))
        log('update', 'lang: %s', str(lang))
        
        metadata.title = media.title

        for s in media.seasons:
          log('update', 'season %s', s)
          seasonMetadata = metadata.seasons[s]
          log('update', 'season metadata %s', seasonMetadata)
          metadata.seasons[s].index = int(s)
          for e in media.seasons[s].episodes:
            log('update', 'episode: %s', e)
            # Make sure metadata exists, and find sidecar media.
            episodeMetadata = metadata.seasons[s].episodes[e]
            log('update', 'episode metadata: %s', episodeMetadata)
            episodeMedia = media.seasons[s].episodes[e].items[0]
        
            file = episodeMedia.parts[0].file
            log('update', 'episode file path: %s', file)
            absFilePath = os.path.abspath(unicodize(file))
            log('update', 'absolute file path: %s', absFilePath)
                  
            # Iterate over the list of parsers and parse the file path
            for parser in SERIES_PARSERS:
                if parser.containsMatch(absFilePath) is True:
                    log('update', 'parser %s contains match - parsing file path', parser)
                    parser.parse(absFilePath, lang)
                    
                    # set the season data
                    log('update', 'before setting season.summary: %s', seasonMetadata.summary)
                    seasonMetadata.summary = parser.getSeasonSummary()
                    log('update', 'season.summary: %s', seasonMetadata.summary)
                    # set the episode data
                    #episodeMetadata.title = parser.getEpisodeTitle()  
                    episodeMetadata.summary = parser.getEpisodeSummary()
                    
                    #log('update', 'episode.title: %s', episodeMetadata.title)
                    log('update', 'episode.summary: %s', episodeMetadata.summary)
                    
                    break
