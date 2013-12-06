import datetime, os, time, re, locale, ConfigParser
from string import Template
#import test

# Series agent name
SERIES_AGENT_NAME = 'Extended Personal Media Shows'

# Date template regex
DATE_TEMPLATE_REGEX = r'(\$\{([_a-z][_a-z0-9]*[\|][^\}]*)\})'
# Date template breakdown regex
DATE_TEMPLATE_BREAKDOWN_REGEX = r'\$\{([_a-z][_a-z0-9]*)[\|]([^\}]*)\}'

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

class CustomParserConfig(object):
    '''
        Finds the configuration for the specified file
    '''
    
    def __init__(self, filePath):
        self.filePath = filePath
        self.config = ConfigParser.SafeConfigParser()
        self.config.read(filePath)
        
    def fileNameRegex(self):
        return self.config.get('parser', 'file.name.regex')

class ConfigMap(object):
    
    def findCustomParser(self, rootDir, filePath):
        customParser = None
        
        configFile = self.findConfigFile(rootDir, filePath)
        if configFile is not None:
            log('__init__', 'found config file %s for media file %s', configFile, filePath)
            # Create the config
            config = CustomParserConfig(configFile)
            # and custom parser
            customParser = CustomMediaParser(config)
            
        return customParser
             
    def findConfigFile(self, rootDir, filePath):
        rootDirFound = False
        parentDir = filePath
        
        # iterate over the directory
        while not rootDirFound:
            # Get the parent directory for the file
            parentDir = os.path.dirname(parentDir)

            log('findConfigFile', 'looking in parent directory %s', parentDir)
            # create the file path
            configFilePath = os.path.normcase(parentDir + '/ext-media.config')
            log('findConfigFile', 'determining whether config file %s exists', configFilePath)
            if os.path.exists(configFilePath) and os.path.isfile(configFilePath):
                log('findConfigFile', 'config file %s exists', configFilePath)
                return configFilePath

            # check to see if this is the root dir
            if parentDir == rootDir:
                rootDirFound = True           
            
class BaseMediaParser(object):
    '''
        Parses the file name and determines the type of tile that was found
    '''
    def setValues(self, match):
        pass

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

                # Determine if the containing directory is numeric and 4 digits long - if so treat it like it's a year                
                self.seasonYear = None
                #match = re.search(YEAR_REGEX, self.seasonTitle)
                #if match:
                    #self.seasonYear = match.group('year')            

                break

    def formatTemplate(self, template, context=None):
        log('formatTemplate', 'template: %s', template)
        log('formatTemplate', 'context: %s', str(context))
        
        # set the locale if it is non-English US region
        log('formatTemplate', 'current locale encoding: %s', locale.getlocale()[1])
        #if self.lang != 'en':
            #log('formatTemplate', 'setting locale to %s', self.lang)
            #locale.setlocale(locale.LC_ALL, self.lang)
            #log('formatTemplate', 'locale.getlocale: %s', locale.getlocale())
        #localeEncoding = locale.getlocale()[1]
        #log('formatTemplate', 'locale encoding: %s', localeEncoding)

        # Find the file name parts
        template_matches = re.findall(DATE_TEMPLATE_REGEX, template)
        for template_match in template_matches:
            log('formatTemplate', 'template match: %s', template_match)
            
            # extract the date format
            date_template_matches = re.findall(DATE_TEMPLATE_BREAKDOWN_REGEX, template)
            for date_template_match in date_template_matches:
                date_format_str = '{0:' + date_template_match[1] + '}'
                log('formatTemplate', 'date format string: %s', date_format_str)
                log('formatTemplate', 'episode date: %s', context['episode_date'])
                formatted_date = date_format_str.format(context['episode_date'])
                #if localeEncoding is not None:
                    #formatted_date = formatted_date.decode(localeEncoding).encode('UTF-8')
                log('formatTemplate', 'formatted date: %s', formatted_date)
                
                template = template.replace(template_match[0], formatted_date, 1)
                log('formatTemplate', 'template after date replace: %s', template)
            
        # Find out what type file format is being used
        t = Template(template)
        retVal = t.safe_substitute(context);
        log('formatTemplate', 'formatted template: %s', retVal)
        return retVal
        
    def getSeasonSummary(self):
        return self.seasonSummary

    def getEpisodeTitle(self):
        return self.episodeTitle

    def getEpisodeSummary(self):
        return self.episodeSummary

class SeriesDateBasedMediaParser(BaseMediaParser):

    def getSupportedRegexes(self):
        return [
                r'(?P<show>[^\\/]+)[\\/](?P<season>[0-9]+)[^\\/]*[\\/][^\\/]*(?P<year>[0-9]{4})[-\. ](?P<month>[0-9]{2})[-\. ](?P<day>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<title>.*)\.(?P<ext>.+)$' , #Show Title\2012\Show Title - 2012-09-19 - Episode Title.mp4, Show Title\2012\2012-09-19 - Episode Title.mp4
                r'(?P<show>[^\\/]+)[\\/](?P<season>[0-9]+)[^\\/]*[\\/][^\\/]*(?P<month>[0-9]{2})[-\. ](?P<day>[0-9]{2})[-\. ](?P<year>[0-9]{4})[ ]*[-\.]{0,1}[ ]*(?P<title>.*)\.(?P<ext>.+)$' , #Show Title\2012\Show Title - 09-19-2013 - Episode Title.mp4, Show Title\2012\09-19-2013 - Episode Title.mp4
                r'(?P<show>[^\\/]+)[\\/](?P<season>[0-9]{4})[\\/][^\\/]*(?P<month>[0-9]{2})[-\. ](?P<day>[0-9]{2})[ ]*[-\.]{0,1}[ ]*(?P<title>.*)\.(?P<ext>.+)$' #Show Title\2012\Show Title - 09-19 - Episode Title.mp4, Show Title\2012\09-19 - Episode Title.mp4
                ]
    
    def setValues(self, match):
        self.episodeTitle = match.group('title').strip()

    def episodeTitle(self):
        # get the episode title template
        template = Prefs['date.parser.episode.title.template']
        context = {'episode_date': self.episodeDate, 'episode_title': self.parsedEpisodeTitle, 'show_title': self.showTitle}
        return self.formatTemplate(template, context)
        
    def episodeSummary(self):
        # get the episode title summary
        template = Prefs['date.parser.episode.summary.template']
        context = {'episode_date': self.episodeDate, 'episode_title': self.parsedEpisodeTitle, 'show_title': self.showTitle}
        return self.formatTemplate(template, context)

class SeriesEpisodeMediaParser(BaseMediaParser):
    
    def getSupportedRegexes(self):
        return [
                r'(?P<show>[^\\/]+)[\\/](?P<season>[0-9]+)[^\\/]*[\\/][^\\/]*[eE](?P<episode>[0-9]+)[ ]*[-\.]{0,1}[ ]*(?P<title>.*)\.(?P<ext>.+)$' #Show Title\2012\Show Title - s2012e09 - Episode Title.mp4
                ] 
    
    def setValues(self, match):
        self.episodeTitle = match.group('title').strip()

    def episodeTitle(self):
        # get the episode title template
        template = Prefs['episode.parser.episode.title.template']
        context = {'episode_title': self.parsedEpisodeTitle, 'show_title': self.showTitle}
        return self.formatTemplate(template, context)

    def episodeSummary(self):
        # get the episode summary template
        template = Prefs['episode.parser.episode.summary.template']
        context = {'episode_title': self.parsedEpisodeTitle, 'show_title': self.showTitle}
        return self.formatTemplate(template, context)
  
class SeriesSimpleMediaParser(BaseMediaParser):
    
    def getSupportedRegexes(self):
        return [
                r'(?P<show>[^\\/]+)[\\/](?P<season>[^\\/]+)[\\/](?P<title>[^\\/]+)\.(?P<ext>.+)$' #Show Title\Season Title\Episode Title.mp4
                ] 
    
    def setValues(self, match):
        self.episodeTitle = match.group('title').strip()

class CustomMediaParser(BaseMediaParser):
    
    episodeMap = {}

    def __init__(self, config):
        self.parserConfig = config
    
    def getSupportedRegexes(self):
        regexes = []
        
        # Check the config to see if a regex has been set
        configRegex = self.parserConfig.fileNameRegex()
        if configRegex is not None:
            regexes.append(configRegex)
            
        # Add the simple regex as the fallback option
        regexes.append(r'(?P<show>[^\\/]+)[\\/](?P<season>[^\\/]+)[\\/](?P<title>[^\\/]+)\.(?P<ext>.+)$')
        log('CustomMediaParser.getSupportedRegexes', 'custom file name regexes in use %s', str(regexes))
        
        return regexes
    
    def setValues(self, match):
        # Set all of the supported values
        self.episodeTitle = match.group('title').strip()

# List of series parsers
SERIES_PARSERS = [SeriesDateBasedMediaParser(), SeriesEpisodeMediaParser(), SeriesSimpleMediaParser()]
# Stores the configuration map
CONFIG_MAP = ConfigMap()

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
            
            parsers = []
            # Check the customParser map for this file
            customParser = CONFIG_MAP.findCustomParser(absRootDir, absFilePath)
            if customParser is not None:
                # If we have a custom parser use only this parser on the file
                parsers = [customParser]
            else:
                # We are using the default parsers
                parsers = SERIES_PARSERS
            
            # Iterate over the list of parsers and parse the file path
            for parser in SERIES_PARSERS:
                if parser.containsMatch(absFilePath) is True:
                    log('update', 'parser %s contains match - parsing file path', parser)
                    parser.parse(absFilePath, lang)
                    
                    episodeMetadata.title = parser.episodeTitle()  
                    episodeMetadata.summary = parser.episodeSummary()
                    
                    log('update', 'episode.title: %s', episodeMetadata.title)
                    log('update', 'episode.summary: %s', episodeMetadata.summary)
