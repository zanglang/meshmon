#!/usr/bin/perl
#
# copyright Dirk Lessner 2006 (Monitoring for NICTA Mesh Router project)
#
# meshtraffic.pl

use 5.008;             # 5.8 required for stable threading
use strict;
use warnings;
use Config;
use Switch;
use IO::File;
use RRDs;
use POSIX qw(strftime);

# global variables

# array of nodes to collect traffic data from
my @Nodes;

# array of interfaces for links to be monitored
my @IF;

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

while(1)
{
	$start = time;
	$starttime = strftime "%H\:%M\:%S", localtime;

	print "Loop started at $starttime\n" if ($debug);

	foreach my $node (@Nodes)
	{
		&ProcessNode(&trim($node));
	}

	$secs = time - $start;
	$stoptime = strftime "%H\:%M\:%S", localtime;
	print "Loop finished at $stoptime, runtime: $secs sec\n\n";
	if ($secs < $interval)
	{
		sleep $interval-($secs);
	}
}

exit;

# Collect traffic data for each eth or ath interface on the particular mobile node
sub ProcessNode
# inputs: $_[0]: IP address of the target
{
	my $target = $_[0];
	my $interface;
	my $ifindex;
	my @temp;

	# get number of WLAN interfaces
	my $wlanint = scalar(@IF);

	# collect the other data for all wlan interfaces
	for (my $i = 0; $i < $wlanint; $i++)
	{
		$interface = trim($IF[$i]);
		$ifindex = `snmpwalk -r $retries -t $timeout -v $snmpversion -c $community $target ifDescr | grep $interface | cut -d"." -f2 | cut -d"=" -f1`;
		chomp $ifindex;
		@temp = ($target, $interface, $ifindex, 0, 0);
		if ($ifindex =~ /[\d]/)
		{
			# Array contains: HostIPAddress, ifDescr, ifIndex, ifInOctets, ifOutOctets
			@temp = ($target, $interface, $ifindex,
				`snmpget -OevQ -r $retries -t $timeout -v $snmpversion -c $community $target ifInOctets.$ifindex`,
				`snmpget -OevQ -r $retries -t $timeout -v $snmpversion -c $community $target ifOutOctets.$ifindex`
				);
			chomp $temp[3];
			chomp $temp[4];
		}
		if ($temp[3] >= 0 && $temp[4] >= 0)
		{
			&ProcessInterface($temp[0], $temp[1], $temp[3], $temp[4]);
		}
		else
		{
			print "Traffic counter value not valid: In $temp[3], Out $temp[4].\n" if ($debug);
		}
		@temp = ();
	}
}

sub ProcessInterface
{
# process wireless interface
# inputs:	$_[0]: host name (ip address)
#		$_[1]: interface name (ie, ath0/ath1/ath2)
#		$_[2]: interface input octets
#		$_[3]: interface output octets
	
	my $ERROR;
	my $heartbeat = $interval * 2;

	print "$_[0]: Interface: $_[1], Input Octets: $_[2], Output Octets: $_[3]\n" if ($debug);

	# if rrdtool database doesn't exist, create it
	if (! -e "$rrd/$_[0]-$_[1].rrd")
	{
		print "Creating rrd database $_[0]-$_[1].rrd...\n" if ($debug);
		RRDs::create "$rrd/$_[0]-$_[1].rrd",
			#"-b now -60s",			# Start time now -1 min
			"-s $interval",			# interval
			"DS:in:COUNTER:$heartbeat:0:3500000",
			"DS:out:COUNTER:$heartbeat:0:3500000",
			"RRA:LAST:0.1:1:720",		# 720 samples of 1 minute (12 hours)
			#"RRA:LAST:0.1:5:576",		# 576 samples of 5 minutes (48 hours)
			"RRA:AVERAGE:0.1:1:720",		# 720 samples of 1 minute (12 hours)
			#"RRA:AVERAGE:0.1:5:576",		# 576 samples of 5 minutes (48 hours)
			"RRA:MAX:0.1:1:720";			# 720 samples of 1 minute (12 hours)
			#"RRA:MAX:0.1:5:576";			# 576 samples of 5 minutes (48 hours)
		if ($ERROR = RRDs::error) { print "$0: failed to create rrd: $ERROR\n"; }
		chmod 0775, "$rrd/$_[0]-$_[1].rrd";
	}

	# insert values into rrd
	print "Updating rrd database $_[0]-$_[1].rrd (in: $_[2], out: $_[3])\n" if ($debug);
	RRDs::update "$rrd/$_[0]-$_[1].rrd",
		"-t",
		"in:out",
		"N:$_[2]:$_[3]";
	if ($ERROR = RRDs::error) { print "$0: failed to insert data into rrd: $ERROR\n"; }

	# create traffic graphs
	&CreateGraphs($_[0], $_[1], "hour");
	#&CreateGraphs($_[0], $_[1], "day");
	#&CreateGraphs($_[0], $_[1], "week");
	#&CreateGraphs($_[0], $_[1], "month");
	#&CreateGraphs($_[0], $_[1], "year");
}

sub CreateGraphs
{
# creates graph
# inputs:	$_[0]: host name (ip address)
#		$_[1]: interface name (ie, ath0/ath1/ath2)
#		$_[2]: interval (ie, day, week, month, year)

	my $ERROR;
	my $now = strftime "%e %b %Y - %H\\:%M\\:%S", localtime;
	my $headline = "Router_".&NodeAddress($_[0])." - $_[1] - ".(($_[2] eq "hour") ? "hourly graph (1 minute average)" : "daily graph (5 minutes average)");
	my $maxline = (($_[2] eq "hour") ? "" : "#FF0000");

	print "Creating graph: $_[0]-$_[1]-$_[2].png.\n" if ($debug);

	# generate link rate graph
	RRDs::graph "$img/$_[0]-$_[1]-$_[2].png",
		"-s -1$_[2]",
		"-t", "$headline",
		"-h", "70",
		"-w", "350",
		"-a", "PNG",
		#"-l", "-20M",
		#"-u", "20M",
		#"--rigid",
		"-v", "Bits/s",
		"DEF:inlast=$rrd/$_[0]-$_[1].rrd:in:LAST",
		"DEF:outlast=$rrd/$_[0]-$_[1].rrd:out:LAST",
		"DEF:inaverage=$rrd/$_[0]-$_[1].rrd:in:AVERAGE",
		"DEF:outaverage=$rrd/$_[0]-$_[1].rrd:out:AVERAGE",
		"DEF:inmax=$rrd/$_[0]-$_[1].rrd:in:MAX",
		"DEF:outmax=$rrd/$_[0]-$_[1].rrd:out:MAX",
		"CDEF:inbitslast=inlast,8,*",
		"CDEF:inbitsaverage=inaverage,8,*",
		"CDEF:inbitsmax=inmax,8,*",
		"CDEF:outbitslast=outlast,8,*",
		"CDEF:outbitsaverage=outaverage,8,*",
		"CDEF:outbitsmax=outmax,8,*",
		"CDEF:outbitsinvlast=outbitslast,-1,*",
		"CDEF:outbitsinvaverage=outbitsaverage,-1,*",
		"CDEF:outbitsinvmax=outbitsmax,-1,*",
		"AREA:inbitsaverage#0000FF:In (last/avg/max)..\\:",
		"LINE1:inbitsmax$maxline",
		"GPRINT:inbitslast:LAST:%5.1lf %sbps",
		"GPRINT:inbitsaverage:AVERAGE:%5.1lf %sbps",
		"GPRINT:inbitsmax:MAX:%5.1lf %sbps\\n",
		"AREA:outbitsinvaverage#00FF00:Out (last/avg/max).\\:",
		"LINE1:outbitsinvmax$maxline",
		"GPRINT:outbitslast:LAST:%5.1lf %sbps",
		"GPRINT:outbitsaverage:AVERAGE:%5.1lf %sbps",
		"GPRINT:outbitsmax:MAX:%5.1lf %sbps\\n",
		"COMMENT:  Last Updated.......\\: $now";
	if ($ERROR = RRDs::error) { print "$0: unable to generate link rate graph: $ERROR\n"; }
	chmod 0775, "$img/$_[0]-$_[1]-$_[2].png";
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
					print "Found list of nodes: @Nodes\n" if ($debug);
				}
				case m/InterfacesLinks/
				{
					@IF = split(/,/, (split(/=/, $_))[1]);
					print "Found list of interfaces for links: @IF\n" if ($debug);
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
				case m/TrafficInterval/
				{
					$interval = trim((split(/=/, $_))[1]);
					print "Found loop interval value: $interval\n" if ($debug);
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
	#print "$_[0]\n";
	#return "";
	return (split(/\./, $_[0]))[3];
}