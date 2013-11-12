import datetime, os, time, re, locale
from string import Template

# Series agent name
SERIES_AGENT_NAME = 'Extended Personal Media Shows'
# Movies agent name
MOVIE_AGENT_NAME = 'Extended Personal Media Movies'

# TV date format regular expression (Show Title - 2012-09-19 - Episode Title)
SERIES_DATE_REGEX_1 = r'^(.*)[\\/]([^\\]+)[\\/](.*)[ ]*[-\.][ ]*([0-9]{4})[-\. ]([0-9]{1,2})[-\. ]([0-9]{1,2})[ ]*[-\.][ ]*(.*)\.(.*)$'
# TV date format regular expression (Show Title - 09-19-2013 - Episode Title)
SERIES_DATE_REGEX_2 = r'^(.*)[\\/]([^\\]+)[\\/](.*)[ ]*[-\.][ ]*([0-9]{1,2})[-\. ]([0-9]{1,2})[-\. ]([0-9]{4})[ ]*[-\.][ ]*(.*)\.(.*)$'
# TV episode format regular expression (Show title - s2012e0919 - Episode Title)
SERIES_EPISODE_REGEX = r'^(.*)[\\/]([^\\]+)[\\/](.*)[ ]*[-\.][ ]*[sS]([0-9]*)[eE]([0-9]*)[ ]*[-\.][ ]*(.*)\.(.*)$'

# Episode name REGEX
TV_EPISODE_NAME_REGEX = r'(.*)[ ]*part|pt[0-9]'

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
    Log('unicodize :: before unicodizing: %s', str(filename))
    if os.path.supports_unicode_filenames:
        try: filename = unicode(s.decode('utf-8'))
        except: pass
    Log('unicodize :: after unicodizing: %s', str(filename))
    return filename

class BaseMediaParser(object):
    '''
        Parses the file name and determines the type of tile that was found
    '''
    
    def __init__(self, mediaFile, lang):
        self.mediaFile = mediaFile
        self.lang = lang
        
    def stripPart(self, s):
        processed = s
        # Test whether it contains part
        if re.match(TV_EPISODE_NAME_REGEX, processed) is not None:
            episodeParts = re.findall(TV_EPISODE_NAME_REGEX, processed)
            Log('stripPart ::  %s', str(episodeParts))
            processed = episodeParts[0].strip()
                
        Log('stripPart :: parsed episode title: %s', processed)
        return processed
        
    def formatTemplate(self, template, context=None):
        Log('formatTemplate :: template: %s', template)
        Log('formatTemplate :: context: %s', str(context))
        
        # set the locale if it is non-English US region
        Log('formatTemplate :: current locale encoding: %s', locale.getlocale()[1])
        #if self.lang != 'en':
            #Log('formatTemplate :: setting locale to %s', self.lang)
            #locale.setlocale(locale.LC_ALL, self.lang)
            #Log('formatTemplate :: locale.getlocale: %s', locale.getlocale())
        #localeEncoding = locale.getlocale()[1]
        #Log('formatTemplate :: locale encoding: %s', localeEncoding)

        # Find the file name parts
        template_matches = re.findall(DATE_TEMPLATE_REGEX, template)
        for template_match in template_matches:
            Log('formatTemplate :: template match: %s', template_match)
            
            # extract the date format
            date_template_matches = re.findall(DATE_TEMPLATE_BREAKDOWN_REGEX, template)
            for date_template_match in date_template_matches:
                date_format_str = '{0:' + date_template_match[1] + '}'
                Log('formatTemplate :: date format string: %s', date_format_str)
                Log('formatTemplate :: episode date: %s', context['episode_date'])
                formatted_date = date_format_str.format(context['episode_date'])
                #if localeEncoding is not None:
                    #formatted_date = formatted_date.decode(localeEncoding).encode('UTF-8')
                Log('formatTemplate :: formatted date: %s', formatted_date)
                
                template = template.replace(template_match[0], formatted_date, 1)
                Log('formatTemplate :: template after date replace: %s', template)
            
        # Find out what type file format is being used
        t = Template(template)
        retVal = t.safe_substitute(context);
        Log('formatTemplate :: formatted template: %s', retVal)
        return retVal
        
    def episodeTitle(self):
        return self.parsedEpisodeTitle
        
    def episodeSummary(self):
        return self.parsedEpisodeTitle
        
class DateBasedMediaParser(BaseMediaParser):

    def __init__(self, mediaFile, lang):
        BaseMediaParser.__init__(self, mediaFile, lang)

        # Find out what type file format is being used
        if re.match(SERIES_DATE_REGEX_1, mediaFile) is not None:
            # Find the file name parts
            fileParts = re.findall(SERIES_DATE_REGEX_1, mediaFile)
            for filePart in fileParts:
                Log('__init__ ::  %s', filePart)
                for p in filePart:
                    Log('__init__ ::  %s', p)
                    
                self.showTitle = filePart[2].strip()
                self.episodeYear = filePart[3].strip()
                self.episodeMonth = filePart[4].strip()
                self.episodeDay = filePart[5].strip()
                self.parsedEpisodeTitle = self.stripPart(filePart[6].strip())
        # Find out what type file format is being used
        elif re.match(SERIES_DATE_REGEX_2, mediaFile) is not None:
            # Find the file name parts
            fileParts = re.findall(SERIES_DATE_REGEX_2, mediaFile)
            for filePart in fileParts:
                Log('__init__ ::  %s', filePart)
                for p in filePart:
                    Log('__init__ ::  %s', p)
                    
                self.showTitle = filePart[2].strip()
                self.episodeMonth = filePart[3].strip()
                self.episodeDay = filePart[4].strip()
                self.episodeYear = filePart[5].strip()
                self.parsedEpisodeTitle = self.stripPart(filePart[6].strip())

        # Create the date
        self.episodeDate = datetime.datetime(int(self.episodeYear), int(self.episodeMonth), int(self.episodeDay))
        Log('__init__ :: episode date: %s', str(self.episodeDate))
                
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
    
    def __init__(self, mediaFile, lang):
        BaseMediaParser.__init__(self, mediaFile, lang)

        # Find the file name parts
        fileParts = re.findall(SERIES_EPISODE_REGEX, mediaFile)
        for filePart in fileParts:
            Log('__init__ :: %s', filePart)
            for p in filePart:
                Log('__init__ ::  %s', p)

            self.showTitle = filePart[2].strip()
            self.episodeSeason = filePart[3].strip()
            self.episodeNumber = filePart[4].strip()
            self.parsedEpisodeTitle = self.stripPart(filePart[5].strip())
            
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
    Log('Start :: starting %s', SERIES_AGENT_NAME)
    pass

class ExtendedPersonalMediaAgentTVShows(Agent.TV_Shows):
    name = SERIES_AGENT_NAME
    languages = Locale.Language.All()
    accepts_from = ['com.plexapp.agents.localmedia']

    def search(self, results, media, lang):
        Log('search :: media id: %s', media.id)
        Log('search :: media file name: %s', str(media.filename))
        Log('search :: media primary metadata: %s', str(media.primary_metadata))
        Log('search :: media primary agent: %s', str(media.primary_agent))
        Log('search :: media title: %s', str(media.title))
        Log('search :: media show: %s', str(media.show))
        Log('search :: media name: %s', str(media.name))
        Log('search :: media season: %s', str(media.season))
        Log('search :: media episode: %s', str(media.episode))
        
        # Compute the GUID based on the media hash.
        try:
            part = media.items[0].parts[0]
            # Get the modification time to use as the year.
            filename = unicodize(part.file)
            Log('search :: part file name: %s', filename)
        except:
            Log('search :: part does not exist')
        
        results.Append(MetadataSearchResult(id=media.id, name=media.show, year=None, lang=lang, score=100))

    def update(self, metadata, media, lang):

        Log('update :: metadata: %s', str(metadata))
        Log('update :: metadata title: %s', str(metadata.title))
        Log('update :: media: %s', str(media))
        Log('update :: media id: %s', media.id)
        Log('update :: media title: %s', str(media.title))
        Log('update :: lang: %s', str(lang))
        
        metadata.title = media.title

        for s in media.seasons:
          Log('update :: creating season %s', s)
          metadata.seasons[s].index = int(s)
          for e in media.seasons[s].episodes:
            Log('update :: episode: %s', e)
            # Make sure metadata exists, and find sidecar media.
            episodeMetadata = metadata.seasons[s].episodes[e]
            Log('update :: episode metadata: %s', episodeMetadata)
            episodeMedia = media.seasons[s].episodes[e].items[0]
            # Parse the file name
            self.parseEpisodeFileName(episodeMetadata, episodeMedia, lang)
            
    def parseEpisodeFileName(self, episodeMetaData, episodeMedia, lang):
        '''
        Parses and stores episode file name parts into the episode metadata
        '''
        
        file = episodeMedia.parts[0].file
        Log('parseEpisodeFileName :: episode file path: %s', file)
        absFilePath = os.path.abspath(unicodize(file))
        Log('parseEpisodeFileName :: absolute file path: %s', absFilePath)
        
        parser = None
        if re.match(SERIES_DATE_REGEX_1, absFilePath) is not None:
            parser = DateBasedMediaParser(absFilePath, lang)
        elif re.match(SERIES_DATE_REGEX_2, absFilePath) is not None:
            parser = DateBasedMediaParser(absFilePath, lang)
        elif re.match(SERIES_EPISODE_REGEX, absFilePath) is not None:
            parser = EpisodeMediaParser(absFilePath, lang)
            
        Log('parseEpisodeFileName :: parser = %s', parser)
        if parser is not None:        
            episodeMetaData.title = parser.episodeTitle()  
            episodeMetaData.summary = parser.episodeSummary()
                
        Log('parseEpisodeFileName :: episode.index = %s', episodeMetaData.index)
        Log('parseEpisodeFileName :: episode.absolute_index = %s', episodeMetaData.absolute_index)
        Log('parseEpisodeFileName :: episode.title: %s', episodeMetaData.title)
        Log('parseEpisodeFileName :: episode.duration: %s', episodeMetaData.duration)
        Log('parseEpisodeFileName :: episode.originally_available_at: %s', episodeMetaData.originally_available_at)
        Log('parseEpisodeFileName :: episode.summary: %s', episodeMetaData.summary)
