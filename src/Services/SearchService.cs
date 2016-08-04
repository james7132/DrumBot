using System.IO;
using System.Text;
using System.Threading.Tasks;
using Discord;
using Discord.Commands;

namespace DrumBot {

    public class SearchService : IService {

        public ChannelSet ChannelSet { get; }

        const string SearchParam = "SearchTerm";

        public SearchService(ChannelSet channels) {
            ChannelSet = Check.NotNull(channels);
        }

        public void Install(DiscordClient client) {

            // Log every public message not made by the bot.
            client.MessageReceived +=
                async (s, e) => {
                    if (e.Message.IsAuthor || e.Channel.IsPrivate)
                        return;
                    await ChannelSet.Get(e.Channel).LogMessage(e.Message);
                };

            // Make sure that every channel is available on loading up a server.
            client.ServerAvailable += delegate(object sender, ServerEventArgs e) {
                foreach (Channel channel in e.Server.TextChannels)
                    ChannelSet.Get(channel);
            };

            var commandService = client.GetService<CommandService>();


            commandService.CreateCommand("search")
                .Description("Search the history of the current channel for a certain value.")
                .Parameter(SearchParam)
                .AddCheck(new ProdChecker())
                .Do(async delegate(CommandEventArgs e) {
                    string reply =await ChannelSet.Get(e.Channel).Search(e.GetArg("SearchTerm"));
                    await e.Respond($"Matches found in {e.Channel.Name}:\n{reply}");
                });

            commandService.CreateGroup("search", cbg => {
                    cbg.CreateCommand("day")
                        .Description("Get the log of the the current channel on a certain day. Day must be of the format ``yyyy-mm-dd``")
                        .Parameter("Day")
                        .AddCheck(new ProdChecker())
                        .Do(GetLog);

                    cbg.CreateCommand("all")
                        .Description("Search the history of the all channels for a certain value.")
                        .Parameter(SearchParam)
                        .AddCheck(new ProdChecker())
                        .Do(SearchAll);
                    
                    cbg.CreateCommand("ignore")
                        .Description("Mentioned channels will not be searched in ``search all``, except while in said channel. "
                            + "User must have ``Manage Channels`` permission")
                        .AddCheck(new ProdChecker())
                        .AddCheck(Check.ManageChannels(bot:false))
                        .Do(async e => {
                            await Config.GetServerConfig(e.Server)
                                .AddIgnoredChannels(e.Message.MentionedChannels);
                            await e.Success();
                        });

                    cbg.CreateCommand("unignore")
                       .Description("Mentioned channels will appear in ``search all`` results." 
                           +" User must have ``Manage Channels`` permission")
                       .AddCheck(new ProdChecker()) 
                       .AddCheck(Check.ManageChannels(bot:false))
                       .Do(async e => {
                           await Config.GetServerConfig(e.Server)
                                .RemoveIgnoredChannels(e.Message.MentionedChannels);
                           await e.Success();
                       });
                });
        }

        async Task GetLog(CommandEventArgs e) {
            string day = e.GetArg("Day");
            string path = ChannelSet.Get(e.Channel).GetPath(day);
            if (File.Exists(path))
                await e.Channel.SendFileRetry(path);
            else
                await e.Channel.SendMessage($"A log for { e.Channel.Mention } on date { day } cannot be found.");
        }

        async Task SearchAll(CommandEventArgs e) {
            var builder = new StringBuilder();
            var serverConfig = Config.GetServerConfig(e.Server);
            foreach (Channel channel in e.Server.TextChannels) {
                if (e.Channel != channel && serverConfig.IsIgnored(channel))
                    continue;
                string result = await ChannelSet.Get(channel).Search(e.GetArg("SearchTerm"));
                if (string.IsNullOrEmpty(result))
                    continue;
                builder.AppendLine($"Matches found in {channel.Name}:");
                builder.AppendLine(result);
            }
            await e.Respond(builder.ToString());
        }
    }
}
