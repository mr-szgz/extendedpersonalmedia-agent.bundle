import datetime, os, time, re, locale
from string import Template
import test

# Series agent name
SERIES_AGENT_NAME = 'Extended Personal Media Shows'
# Movies agent name
MOVIE_AGENT_NAME = 'Extended Personal Media Movies'

# Series date format regular expression (Show Title - 2012-09-19 - Episode Title)
SERIES_DATE_REGEX_1 = r'^(?P<baseDir>.*)[\\/](?P<dirShow>[^\\]+)[\\/](?P<dirSeason>[^\\]+)[\\/](?P<show>.*)[ ]*[-\.][ ]*(?P<year>[0-9]{4})[-\. ](?P<month>[0-9]{1,2})[-\. ](?P<day>[0-9]{1,2})[ ]*[-\.][ ]*(?P<title>.*)\.(?P<ext>.*)$'
# Series date format regular expression (Show Title - 09-19-2013 - Episode Title)
SERIES_DATE_REGEX_2 = r'^(?P<baseDir>.*)[\\/](?P<dirShow>[^\\]+)[\\/](?P<dirSeason>[^\\]+)[\\/](?P<show>.*)[ ]*[-\.][ ]*(?P<month>[0-9]{1,2})[-\. ](?P<day>[0-9]{1,2})[-\. ](?P<year>[0-9]{4})[ ]*[-\.][ ]*(?P<title>.*)\.(?P<ext>.*)$'
# Series episode format regular expression (Show title - s2012e0919 - Episode Title)
SERIES_EPISODE_REGEX = r'^(?P<baseDir>.*)[\\/](?P<dirShow>[^\\]+)[\\/](?P<dirSeason>[^\\]+)[\\/](?P<show>.*)[ ]*[-\.][ ]*[sS](?P<season>[0-9]*)[eE](?P<episode>[0-9]*)[ ]*[-\.][ ]*(?P<title>.*)\.(?P<ext>.*)$'

# List of series parsers
SERIES_PARSERS = [DateBasedMediaParser(), EpisodeMediaParser()]

# Series date format regular expression (Show Title - 2012-09-19 - Episode Title)
MOVIES_DATE_REGEX_1 = r'^(?P<baseDir>.*)[\\/](?P<dirShow>[^\\]+)[\\/](?P<show>.*)[ ]*[-\.][ ]*(?P<year>[0-9]{4})[-\. ](?P<month>[0-9]{1,2})[-\. ](?P<day>[0-9]{1,2})[ ]*[-\.][ ]*(?P<title>.*)\.(?P<ext>.*)$'
# Series date format regular expression (Show Title - 09-19-2013 - Episode Title)
MOVIES_DATE_REGEX_2 = r'^(?P<baseDir>.*)[\\/](?P<dirShow>[^\\]+)[\\/](?P<show>.*)[ ]*[-\.][ ]*(?P<month>[0-9]{1,2})[-\. ](?P<day>[0-9]{1,2})[-\. ](?P<year>[0-9]{4})[ ]*[-\.][ ]*(?P<title>.*)\.(?P<ext>.*)$'

# List of movie parsers
MOVIES_PARSERS = [DateBasedMediaParser()]

# Episode name REGEX
SERIES_EPISODE_TITLE_PART_REGEX = r'(?P<title>.*)[ ]*part|pt[0-9]'

# Date template regex
DATE_TEMPLATE_REGEX = r'(\$\{([_a-z][_a-z0-9]*[\|][^\}]*)\})'
# Date template breakdown regex
DATE_TEMPLATE_BREAKDOWN_REGEX = r'\$\{([_a-z][_a-z0-9]*)[\|]([^\}]*)\}'


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

def log(methodName, message, *args):
    Log(methodName + ' :: ' + message, *args)

class BaseMediaParser(object):
    '''
        Parses the file name and determines the type of tile that was found
    '''
    
    def containsMatch(self, mediaFile):
        retVal = False
        # Iterate over the list of regular expressions
        for regex in supportedRegexes:
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
        for regex in supportedRegexes:
            # Find out what file format is being used
            match = re.search(regex, mediaFile)
            if match:
                setValues(match)
                break

    def setValues(self, match):
        pass

    def getSupportedRegexes(self):
        return []
        
    def stripPart(self, s):
        retVal = s
        # Test whether it contains part
        match = re.search(SERIES_EPISODE_TITLE_PART_REGEX, retVal)
        if match:
            Log('stripPart', 'title matched')
            retVal = match('title').strip()
                
        Log('stripPart', 'parsed episode title: %s', retVal)
        return retVal
        
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
        
    def episodeTitle(self):
        return self.parsedEpisodeTitle
        
    def episodeSummary(self):
        return self.parsedEpisodeTitle
      
class MoviesDateBasedMediaParser(BaseMediaParser):
    
    def getSupportedRegexes(self):
        return [MOVIES_DATE_REGEX_1, MOVIES_DATE_REGEX_2]
    
    def setValues(self, match):
        self.showTitle = match('show').strip()
        self.episodeYear = match('year').strip()
        self.episodeMonth = match('month').strip()
        self.episodeDay = match('day').strip()
        self.parsedEpisodeTitle = self.stripPart(match('title').strip())
        # Create the date
        self.episodeDate = datetime.datetime(int(self.episodeYear), int(self.episodeMonth), int(self.episodeDay))
        Log('parse', 'episode date: %s', str(self.episodeDate))

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
        
class SeriesDateBasedMediaParser(BaseMediaParser):
    
    def getSupportedRegexes(self):
        return [SERIES_DATE_REGEX_1, SERIES_DATE_REGEX_2]
    
    def setValues(self, match):
        self.showTitle = match('show').strip()
        self.episodeYear = match('year').strip()
        self.episodeMonth = match('month').strip()
        self.episodeDay = match('day').strip()
        self.parsedEpisodeTitle = self.stripPart(match('title').strip())
        # Create the date
        self.episodeDate = datetime.datetime(int(self.episodeYear), int(self.episodeMonth), int(self.episodeDay))
        Log('parse', 'episode date: %s', str(self.episodeDate))

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

class EpisodeMediaParser(BaseMediaParser):
    
    def getSupportedRegexes(self):
        return [SERIES_EPISODE_REGEX] 
    
    def setValues(self, match):
        self.showTitle = match('show').strip()
        self.episodeSeason = match('season').strip()
        self.episodeNumber = match('episode').strip()
        self.parsedEpisodeTitle = self.stripPart(match('title').strip())
            
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
    
def Start():
    log('Start', 'starting agents %s, %s', SERIES_AGENT_NAME, MOVIE_AGENT_NAME)
    test.test('Extended Personal Media - Scan')
    pass

class ExtendedPersonalMediaAgentMovies(Agent.Movies):
    name = MOVIE_AGENT_NAME
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
        part = media.items[0].parts[0]
        
        # Get the modification time to use as the year.
        fileName = unicodize(part.file)
        lastModifiedTimestamp = os.path.getmtime(fileName)
        log('search', 'part.hash: %s', part.hash)
        
        results.Append(MetadataSearchResult(id=part.hash, name=media.name, year=time.localtime(lastModifiedTimestamp)[0], lang=lang, score=100))
        
    def update(self, metadata, media, lang):
        log('update', 'metadata: %s', str(metadata))
        log('update', 'media: %s', str(media))
        log('update', 'lang: %s', str(lang))

        # Get the filename and the mod time.
        filename = unicodize(media.items[0].parts[0].file)

        lastModifiedTimestamp = os.path.getmtime(filename)
        lastModifiedDate = datetime.date.fromtimestamp(lastModifiedTimestamp)
        
        # Fill in the little we can get from a file.
        try: title = os.path.splitext(os.path.basename(filename))[0]
        except: title = media.title
          
        # Set the default values based on the file attributes
        metadata.title = title
        metadata.summary = title
        metadata.year = lastModifiedDate.year
        metadata.originally_available_at = Datetime.ParseDate(str(lastModifiedDate)).date()
        
        # Iterate over the list of parsers and parse the file path
        for parser in MOVIES_PARSERS:
            if parser.containsMatch(absFilePath) is True:
                log('update', 'parser %s contains match - parsing file path', parser)
                parser.parse(absFilePath, lang)

                metadata.title = parser.episodeTitle()
                metadata.summary = parser.episodeSummary()
                metadata.year = parser.episodeDate.year
                metadata.originally_available_at = parser.episodeDate
                
        log('update', 'metadata.title: %s', metadata.title)
        log('update', 'metadata.summary: %s', metadata.summary)
        log('update', 'metadata.year: %s', metadata.year)
        log('update', 'metadata.originally_available_at: %s', metadata.originally_available_at)

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
            
            # Iterate over the list of parsers and parse the file path
            for parser in SERIES_PARSERS:
                if parser.containsMatch(absFilePath) is True:
                    log('update', 'parser %s contains match - parsing file path', parser)
                    parser.parse(absFilePath, lang)
                    
                    episodeMetaData.title = parser.episodeTitle()  
                    episodeMetaData.summary = parser.episodeSummary()
                    
                    log('update', 'episode.title: %s', episodeMetaData.title)
                    log('update', 'episode.summary: %s', episodeMetaData.summary)
