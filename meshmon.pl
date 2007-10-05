#!/usr/bin/perl
#
# copyright Dirk Lessner 2006 (Monitoring for NICTA Mesh Router project)
#
# meshmon.pl

use 5.008;             # 5.8 required for stable threading
use strict;
use warnings;
use Config;
use threads;
use Switch;
use IO::File;
use RRDs;
use POSIX qw(strftime);

# global variables

# array of nodes to collect traffic data from
my @Nodes;

# array of nodes to collect link data from
my @NodeLinks;

# array of link information from each monitored node
my @Links;

# array of interfaces for links to be monitored
my @IF;

# array of interfaces for traffic to be monitored
my @IFT;

# array of host numbers as part of the IP address
my @Hosts;

# IP address of the camera
my $CameraIP;

# IP address of the handheld
my $HandheldIP;

# IP address of the mobile phone
my $PhoneIP;

# array of threads
#my @Threads;

# Interval for collecting traffic data in seconds
my $interval;

# version of SNMP [1|2c|3]
my $snmpversion;

# read-only community string
my $community;

# location of rrdtool databases
my $rrd;

# define location of images
my $img;

# Debug mode on|off (1|0)
my $debug;

# Bandwidth value (payload) for the wireless link
my $bw;

# Defines the SNMP timeout in seconds
my $timeout;

# Defines the SNMP retries
my $retries;

# Starttime of the loop in Unix seconds 
my $start;

# Runtime of the loop 
my $secs;

# Starttime of the loop as a formated string 
my $starttime;

# Stoptime of the loop as a formated string 
my $stoptime;

&ReadConfig();

# Create HTML Webpage
open(FH, ">", "$img/index.html") || die "Can't open file $img/index.html $!";
print FH &MakeHTML;
close(FH) || die "Can't close file $img/index.html $!";

# endless loop
while(1)
{
	my @Threads;

	$start = time;
	$starttime = strftime "%H\:%M\:%S", localtime;

	print "Loop started at $starttime\n" if ($debug);

	# collect data for all interfaces of one node, each in a separate thread
	foreach my $node (@NodeLinks)
	{
		#push @Links, &ProcessNode(&trim($node));
		push @Threads, threads->new(\&ProcessNode, &trim($node));
	}

	foreach my $thread (@Threads)
	{
		push @Links, $thread->join;
	}

	print "Creating configuration file $rrd/weathermap.conf for topology graph.\n" if ($debug);
	open(FH, ">", "$rrd/weathermap.conf") || die "Can't open file $rrd/weathermap.conf $!";
	print FH &MakeWeathermapConf;
	close(FH) || die "Can't close file $rrd/weathermap.conf $!";
	
	print "Creating topology graph $img/weathermap.png.\n" if ($debug);
	system("$rrd/weathermap.pl");
	system("cp $img/weathermap-new.png $img/weathermap.png");

	if (!$debug)
	{
		foreach my $L (@Links)
		{
			&PrintValues($L);
		}
	}

	@Links = ();

	$secs = time - $start;
	$stoptime = strftime "%H\:%M\:%S", localtime;
	print "Loop finished at $stoptime, runtime: $secs sec\n\n";
	if ($secs < $interval)
	{
		sleep $interval-($secs);
	}
}

exit;

# inputs: $_[0]: IP address of the target
sub ProcessNode
{
	my $target = $_[0];
	my @WLAN;
	my $ifindex;
	my $interface;

	# get number of WLAN interfaces
	my $wlanint = scalar(@IF);
	
	print "Thread $target (@IF) started....\n" if ($debug);

	# get ip address of the neighbour hosts
	my @ipnind = (split(/\n/, `snmpwalk -OevQ -r $retries -t $timeout -v $snmpversion -c $community $target ipRouteIfIndex`));
	my @ipnaddr = (split(/\n/, `snmpwalk -OevQ -r $retries -t $timeout -v $snmpversion -c $community $target ipRouteDest`));

	print "Thread $target: [Depth=0] Routingtable: @ipnaddr.\n" if ($debug);
	print "Thread $target: [Depth=0] Index: @ipnind.\n" if ($debug);

	# collect data from the specified interfaces
	for (my $i = 0; $i < $wlanint; $i++)
	{
		$interface = trim($IF[$i]);
		$ifindex = `snmpwalk -r $retries -t $timeout -v $snmpversion -c $community $target ifDescr | grep $interface | cut -d"." -f2 | cut -d"=" -f1`;
		chomp $ifindex;
		print "Thread $target: [Depth=1] Collect data from $interface with index $ifindex.\n" if ($debug);
		if ($ifindex =~ /[\d]/)
		{
			my $AdmStatus = trim(`snmpget -OevQ -v $snmpversion -c $community $target ifAdminStatus.$ifindex`);
			print "Thread $target: [Depth=2] Admin status of interface $interface is $AdmStatus.\n" if ($debug);
			if ($AdmStatus == 1)
			{
				# Array contains: HostIPAddress, ifDescr, ifIndex, ListOfNeighbours
				my @temp = ($target, $interface, trim($ifindex));

				if (scalar(@ipnaddr) == scalar(@ipnind))
				{
					# iterate through all routes
					for (my $j = 0; $j < scalar(@ipnaddr); $j++)
					{
						# is ipRouteIfIndex = ifIndex?
						print "Thread $target: [Depth=4] Is route $j via $interface? ".(($ipnind[$j] == $ifindex) ? "Yes" : "No")."\n" if ($debug);
						if ($ipnind[$j] == $ifindex)
						{
							# is ipRouteType = direct (3)
							my $ipRouteType = `snmpget -OevQ -r $retries -t $timeout -v $snmpversion -c $community $target ipRouteType.$ipnaddr[$j]`;
							chomp $ipRouteType;
							print "Thread $target: [Depth=5] Route type: $ipRouteType (2=invalid, 3=direct, 4=indirect).\n" if ($debug);
							if ($ipRouteType =~ /[34]/)
							{
								# is ipRouteMask a host route (255.255.255.255)
								my $ipRouteMask = `snmpget -OevQ -r $retries -t $timeout -v $snmpversion -c $community $target ipRouteMask.$ipnaddr[$j]`;
								chomp $ipRouteMask;
								print "Thread $target: [Depth=6] Is route a hostroute? ".($ipRouteMask =~ /255.255.255.255/ ? "Yes" : "No")." ($ipRouteMask)\n" if ($debug);
								if ($ipRouteMask eq "255.255.255.255")
								{
									print "Thread $target: [Depth=7] Add $ipnaddr[$j] as neighbour.\n" if ($debug);
									push @temp, $ipnaddr[$j];
								}
							}
						}
					}
					print "Thread $target: Add info: @temp.\n" if ($debug);
					push @WLAN, [@temp];
				}
				else
				{
					print "Thread $target: [Depth=3] Entries in routing table not equal to entries in index table.\n" if ($debug);
					last;
				}
			}
		}
		else
		{
			print "Thread $target: [Depth=1] The interface index '$ifindex' is not valid.\n" if ($debug);
			last;
		}
	}
	print "Thread $target (@IF) finished....\n" if ($debug);
	return @WLAN;
}

# Reads global variables from the config file (meshmon.conf)
sub ReadConfig
{
	my $file = "/var/lib/meshmon/meshmon.conf";
	print "Reading configuration file $file\n";
	open (INPUT, $file) || die "Can't open $file: $!\n";
	while (<INPUT>)
	{
		chomp;
		if ($_ !~ /^#/)
		{
			switch ($_)
			{
				case m/Debug/
				{
					$debug = trim((split(/=/, $_))[1]);
					print "Found debug value: $debug\n" if ($debug);
				}
				case m/NodeTraffic/
				{
					@Nodes = split(/,/, (split(/=/, $_))[1]);
					foreach my $node (@Nodes)
					{
						push @Hosts, &NodeAddress(trim($node));
					}
					print "Found list of nodes: @Nodes\n" if ($debug);
					print "Found list of hosts: @Hosts\n" if ($debug);
				}
				case m/NodeLink/
				{
					@NodeLinks = split(/,/, (split(/=/, $_))[1]);
					print "Found list of hosts to monitor: @NodeLinks\n" if ($debug);
				}
				case m/InterfacesLinks/
				{
					@IF = split(/,/, (split(/=/, $_))[1]);
					print "Found list of interfaces for link monitoring: @IF\n" if ($debug);
				}
				case m/InterfacesTraffic/
				{
					@IFT = split(/,/, (split(/=/, $_))[1]);
					print "Found list of interfacesfor traffic monitoring: @IFT\n" if ($debug);
				}
				case m/CameraIP/
				{
					$CameraIP = trim((split(/=/, $_))[1]);
					print "Found camera IP address: $CameraIP\n" if ($debug);
				}
				case m/HandheldIP/
				{
					$HandheldIP = trim((split(/=/, $_))[1]);
					print "Found handheld IP address: $HandheldIP\n" if ($debug);
				}
				case m/PhoneIP/
				{
					$PhoneIP = trim((split(/=/, $_))[1]);
					print "Found mobile phone IP address: $PhoneIP\n" if ($debug);
				}
				case m/SnmpVersion/
				{
					$snmpversion = trim((split(/=/, $_))[1]);
					print "Found SnmpVersion: $snmpversion\n" if ($debug);
				}
				case m/Community/
				{
					$community = trim((split(/=/, $_))[1]);
					print "Found SnmpCommunity: $community\n" if ($debug);
				}
				case m/SnmpTimeout/
				{
					$timeout = trim((split(/=/, $_))[1]);
					print "Found SNMP timeout value: $timeout\n" if ($debug);
				}
				case m/SnmpRetries/
				{
					$retries = trim((split(/=/, $_))[1]);
					print "Found SNMP retry value: $retries\n" if ($debug);
				}
				case m/LinkInterval/
				{
					$interval = trim((split(/=/, $_))[1]);
					print "Found loop interval value: $interval\n" if ($debug);
				}
				case m/Bandwidth/
				{
					$bw = trim((split(/=/, $_))[1]);
					print "Found bandwidth value: $bw\n" if ($debug);
				}
				case m/RrdDir/
				{
					$rrd = trim((split(/=/, $_))[1]);
					print "Found script and database directory: $rrd\n" if ($debug);
				}
				case m/ImgDir/
				{
					$img = trim((split(/=/, $_))[1]);
					print "Found image directory: $img\n" if ($debug);
				}
			}
		}
	}
	print "Closing configuration file $file\n\n" if ($debug);
	close(INPUT) || die "Can't close $file: $!\n";
}

# Perl trim function to remove whitespace from the start and end of the string
sub trim($)
{
	my $string = shift;
	$string =~ s/^\s+//;
	$string =~ s/\s+$//;
	return $string;
}

# Left trim function to remove leading whitespace
sub ltrim($)
{
	my $string = shift;
	$string =~ s/^\s+//;
	return $string;
}

# Right trim function to remove trailing whitespace
sub rtrim($)
{
	my $string = shift;
	$string =~ s/\s+$//;
	return $string;
}

# Returns the host address part from a full IP address (assume a Class-C net) 
sub NodeAddress
{
	return (split(/\./, $_[0]))[3];
}

sub NodeNet
{
	return (split(/\./, $_[0]))[2];
}

# Prints an array
sub PrintValues
{
	foreach my $if (@_)
	{
		print "@$if\n";
	}
}

# generates the weathermap config file
sub MakeWeathermapConf
{
my $conf =
"#BACKGROUND icons/NICTA.png

# Size of image generated if no background has been defined. If one background is defined, size of background will be used.
HEIGHT 720
WIDTH 500

# FONT from 1 to 5 (define size of font that will be used in graph)
FONT 2

# Position of legend
KEYPOS 375 10

# Width of the Link Arrows
LINKWIDTH 4

# HTML file
HTMLFILE $img/weathermap.html

# label of TITLE
#TITLE \"NICTA MESH Router Topology Map\"
# Position of title in graph
TITLEPOS 130 685
# Color of background title
#TITLEBACKGROUND 0 192 0
# Color of font to display title
TITLEFOREGROUND 0 0 0

# Define path and name of a png file on server. You may comment this line if you don't want to keep a file of graph.
OUTPUTFILE $img/weathermap-new.png

#     low  high   red green blue
#SCALE   1   10    140     0  255
#SCALE  10   25     32    32  255
#SCALE  25   40      0   192  255
#SCALE  40   55      0   240    0
#SCALE  55   70    240   240    0
#SCALE  70   85    255   192    0
#SCALE  85  100    255     0    0

SCALE   1   100      0     0  192

# Define Nodes
# NICTA Logo dimension: 168px x 60px
NODE logo
#       POSITION 250 375
       POSITION 84 30
	ICON $rrd/icons/NICTA-small.png
	ICONTPT 100

";

my $hosts = scalar(@Hosts);

print "Creating list of $hosts nodes.\n" if ($debug);

$conf .= "NODE Camera\n\tPOSITION 250 60\n\tLABEL\n\tICON $rrd/icons/AXIS207w.png\n\tICONTPT 100\n\n";
$conf .= "NODE Handheld\n\tPOSITION 150 660\n\tLABEL\n\tICON $rrd/icons/ux172.png\n\tICONTPT 100\n\n";
$conf .= "NODE Phone\n\tPOSITION 350 660\n\tLABEL\n\tICON $rrd/icons/nokia_n93_01.png\n\tICONTPT 100\n\n";

if ($hosts >= 1)
{
	$conf .= "NODE MN$Hosts[0]\n\tPOSITION 75 360\n\tLABEL Router_$Hosts[0]\n\tICON $rrd/icons/Safemesh1.png\n\tICONTPT 100\n\n";
}

if ($hosts >= 2)
{
	$conf .= "NODE MN$Hosts[1]\n\tPOSITION 250 200\n\tLABEL Router_$Hosts[1]\n\tICON $rrd/icons/Safemesh1.png\n\tICONTPT 100\n\n";
}

if ($hosts >= 3)
{
	$conf .= "NODE MN$Hosts[2]\n\tPOSITION 425 360\n\tLABEL Router_$Hosts[2]\n\tICON $rrd/icons/Safemesh1.png\n\tICONTPT 100\n\n";
}

if ($hosts >= 4)
{
	$conf .= "NODE MN$Hosts[3]\n\tPOSITION 250 520\n\tLABEL Router_$Hosts[3]\n\tICON $rrd/icons/Safemesh1.png\n\tICONTPT 100\n\n";
}

my $Nodes = scalar(@Links);
my @ShowLinks;
my $Link;

print "Creating list of links.\n" if ($debug);

for (my $i = 0; $i < $Nodes; $i++)
{
	my $LinkCnt = @{$Links[$i]};
	my $links = $LinkCnt - 3;
	print "Found $links links: @{$Links[$i]}\n" if ($debug && ($links > 0));
	for (my $j = 3; $j < $LinkCnt; $j++)
	{
		my $from = &NodeAddress($Links[$i][0]);
		my $to = &NodeAddress($Links[$i][$j]);

		if ($Links[$i][$j] eq $HandheldIP)
		{
			$from = &NodeAddress($Links[$i][0]);
			$to = "Handheld";
			print "Print link $from-$to.\n" if ($debug);
			$Link =	"LINK MN$from$Links[$i][1]-$to\n".
					"\tNODES MN$from $to\n".
					"\tTARGET $rrd/$Links[$i][0]-$Links[$i][1].rrd\n".
					"\tINPOS 1\n".
					"\tOUTPOS 2\n".
					"\tUNIT bytes\n".
					"\tBANDWIDTH $bw\n".
					"\tDISPLAYVALUE 0\n".
					"\tARROW normal\n\n";
			$conf .= $Link;
		}

		if ($Links[$i][$j] eq $PhoneIP)
		{
			$from = &NodeAddress($Links[$i][0]);
			$to = "Phone";
			print "Print link $from-$to.\n" if ($debug);
			$Link =	"LINK MN$from$Links[$i][1]-$to\n".
					"\tNODES MN$from $to\n".
					"\tTARGET $rrd/$Links[$i][0]-$Links[$i][1].rrd\n".
					"\tINPOS 1\n".
					"\tOUTPOS 2\n".
					"\tUNIT bytes\n".
					"\tBANDWIDTH $bw\n".
					"\tDISPLAYVALUE 0\n".
					"\tARROW normal\n\n";
			$conf .= $Link;
		}

		if ($to == 8)
		{
			$Link =	"LINK MN$from$Links[$i][1]-MN$to\n".
					"\tNODES MN$from MN$to\n".
					"\tTARGET $rrd/$Links[$i][0]-$Links[$i][1].rrd\n".
					"\tINPOS 1\n".
					"\tOUTPOS 2\n".
					"\tUNIT bytes\n".
					"\tBANDWIDTH $bw\n".
					"\tDISPLAYVALUE 0\n".
					"\tARROW normal\n\n".
					"LINK MN$to-MN7\n".
					"\tNODES MN$to MN7\n".
					"\tTARGET $rrd/$Links[$i][0]-$Links[$i][1].rrd\n".
					"\tINPOS 1\n".
					"\tOUTPOS 2\n".
					"\tUNIT bytes\n".
					"\tBANDWIDTH $bw\n".
					"\tDISPLAYVALUE 0\n".
					"\tARROW normal\n\n";
			$conf .= $Link;
		}

		if ($to == 4)
		{
			$Link =	"LINK MN$from$Links[$i][1]-MN$to\n".
					"\tNODES MN$from MN$to\n".
					"\tTARGET $rrd/$Links[$i][0]-$Links[$i][1].rrd\n".
					"\tINPOS 1\n".
					"\tOUTPOS 2\n".
					"\tUNIT bytes\n".
					"\tBANDWIDTH $bw\n".
					"\tDISPLAYVALUE 0\n".
					"\tARROW normal\n\n".
					"LINK MN$to-MN7\n".
					"\tNODES MN$to MN7\n".
					"\tTARGET $rrd/$Links[$i][0]-$Links[$i][1].rrd\n".
					"\tINPOS 1\n".
					"\tOUTPOS 2\n".
					"\tUNIT bytes\n".
					"\tBANDWIDTH $bw\n".
					"\tDISPLAYVALUE 0\n".
					"\tARROW normal\n\n";
			$conf .= $Link;
		}

		#if ($Links[$i][$j] eq $CameraIP)
		if ($to =~ /[48]/)
		{
			$from = 7;
			$to = "Camera";
			print "Print link $from-$to.\n" if ($debug);
			$Link =	"LINK MN$from$Links[$i][1]-$to\n".
					"\tNODES MN$from $to\n".
					"\tTARGET $rrd/$Links[$i][0]-$Links[$i][1].rrd\n".
					"\tINPOS 1\n".
					"\tOUTPOS 2\n".
					"\tUNIT bytes\n".
					"\tBANDWIDTH $bw\n".
					"\tDISPLAYVALUE 0\n".
					"\tARROW normal\n\n";
			$conf .= $Link;
		}
	}
}

return $conf;
}

# generates the HTML file
sub MakeHTML
{
print "Creating HTML page $img/index.html\n" if ($debug);
my $html1 =
"<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Strict//EN\"\"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd\">
<html xmlns=\"http://www.w3.org/1999/xhtml\">
	<head>
		<META HTTP-EQUIV=\"Refresh\" CONTENT=\"2\">
		<META HTTP-EQUIV=\"Pragma\" CONTENT=\"no-cache\">
		<META HTTP-EQUIV=\"Cache-Control\" content=\"no-cache\">
		<link href=\"index.css\" rel=\"stylesheet\" type=\"text/css\" />
		<title>NICTA MESH Router Monitoring</title>
	</head>
	<body>
		<div id=\"Topology\">
			SAFE MESH Network Topology<br />
			<img src=\"weathermap.png\" alt=\"The Topology Map is currently unavailable\" />
		</div>
";

my $html2 = 
"	</body>
</html>";

return $html1.&HLinks.$html2;
}

sub HLinks
{
	my $html = "\t\t<div id=\"TrafficH\">\n\t\t\tTraffic Graphs<br />\n";

	for (my $i = 0; $i < scalar(@Nodes); $i++)
	{
		my $node = trim($Nodes[$i]);
		for (my $j = 0; $j < scalar(@IFT); $j++)
		{
			my $interface = trim($IFT[$j]);
			$html .= "\t\t\t<img src=\"$node-$interface-hour.png\" alt=\"$node - $interface (no graph)\" />";
			if ($j == (scalar(@IFT) - 1))
			{
				$html .= "<br />\n";
			}
			else
			{
				$html .= "\n";
			}
		}
	}

	$html .= "\t\t</div>\n";
	return $html;
}
