#!/usr/bin/perl
# Weathermap4rrd 
# Alexandre Fontelle, <afontelle AT free.fr>
# http://weathermap4rrd.tropicalex.net
# based on Network Wearthermap - version 1.1.1 from Panagiotis Christias (http://netmon.grnet.gr/weathermap/)
# modified for RRDTool use and other stuff

$VERSION = "1.2RC3";

use Getopt::Long;
use GD;
use RRDs;
use POSIX;
use POSIX qw(strftime);

################################################################
#
# Configuration parameters
#
$CONFIG = "weathermap.conf";    # Default value if nothing is specified in config file
$OUTPUTFILE = "weathermap.png"; # Default value if nothing is specified in config file
$DEBUG  = 0;
$LINKWIDTH = 4; # Default width for the link arrows
$WIDTH  = 740; # Default value if nothing is specified in config file
$HEIGHT = 600;  # Default value if nothing is specified in config file
$DATE 	= "now";
$FONT	= gdLargeFont;
$RRDTOOL_PATH = "/usr/bin/";
################################################################

%optctl=();

GetOptions(\%optctl, "config:s", "output:s", "date:s", "version", "group:s", "help", "debug", "") || exit(1);

if($optctl{"config"}) { $CONFIG = $optctl{"config"} };

if($optctl{"output"}) { $OUTPUTFILE = $optctl{"output"} };

#if($optctl{"date"}) { 
#	$DATE = `/bin/date --date="$optctl{"date"}" +%s`; 
#} else {
#	$DATE = strftime "%e %b %Y - %H:%M:%S", localtime;
	$DATE = time;
#}

print "Date: ".(strftime "%e %b %Y - %H\:%M\:%S", localtime($DATE))." ($DATE)\n" if ($DEBUG);

if($optctl{"version"}) { &version; exit; }

if($optctl{"group"}) { 
	$filter=$optctl{"group"}; 
	print "DEBUG : filter for group $filter\n" if ($DEBUG);
}

if($optctl{"help"}) { &usage; exit; }

if($optctl{"debug"}) { $DEBUG=1; }

if ($DEBUG) { print "Weathermap4rrd $version"; }

&read_config($CONFIG);

if($background){
	open (PNG,"$background") || die "$background: $!\n";
	$map = newFromPng GD::Image(PNG) || die "newFromPng failed.";
	close PNG;
} else {
	$map=new GD::Image($WIDTH,$HEIGHT)
}

if(! $titlebackground_red) {
	$titlebackground_red=255;
	$titlebackground_green=255;
	$titlebackground_blue=255;
}

if(! $titleforeground_red) {
	$titleforeground_red=0;
	$titleforeground_green=0;
	$titleforeground_blue=0;
}


#$maxColors = $map->colorsTotal;
#print "Colours: $maxColors\n";
&alloc_colors;

#$map->transparent($white);

if ( $GD::VERSION > 2 ) {
	# Anti-aliasing enable
	gdAntiAliased();
	$map->setAntiAliased($white);

	# to disable anti-aliasing
	#$map->setAntiAliasedDontBlend($color,0);
	#print "ok ".$GD::VERSION."\n";
}

print "Reading rrd files...\n\n" if($DEBUG);
foreach $link (keys %target){
	$data = $target{$link};
	print "FILE: $data\n" if($DEBUG);
	if ( ! $DATE ) {
		$DATE= RRDs::last "$data";
		$version=&rrdtool_getversion();
		print "RRDTool binary version detected : $version\n" if ($DEBUG);
		if ($version=="1.2") {
			$DATE= $DATE-300;
		}
		print "No date specified, last value will be read : ".scalar localtime($DATE)."\n" if ($DEBUG);
	}
	my ($start,$step,$names,$data) = RRDs::fetch "$data","AVERAGE","--start","$DATE-2min","--end","$DATE";
	my $ERR=RRDs::error;
	die "W4RRD ERROR while reading $target{$link}: $ERR\n" if $ERR;
	print "Start:       ", scalar localtime($start), " ($start)\n"  if($DEBUG);
	print "Step size:   $step seconds\n"  if($DEBUG);
	print "DS names:    ", join (", ", @$names)."\n"  if($DEBUG);
	print "Data points: ", $#$data + 1, "\n"  if($DEBUG);
	foreach my $line (@$data) {
		if(@$line[0] != null) {
			$input{$link}=@$line[$inpos{$link}-1]*$coef{$link};
			$output{$link}=@$line[$outpos{$link}-1]*$coef{$link};
			print "LINK: $link, Input: $input{$link}\n" if($DEBUG);
			print "LINK: $link, Output: $output{$link}\n" if($DEBUG);
		}
	}
}
print "\nDisplaying icons...\n\n" if($DEBUG);
foreach $node (keys %iconpng){
	if ($iconpng{$node} && (-e $iconpng{$node}) ) {
		open (ICON,$iconpng{$node}) || warn "$iconpng{$node}: $!\n";
			$icone = newFromPng GD::Image(ICON);
			($IconWidth,$IconHeight) = $icone->getBounds;

			$factor=$iconresize{$node}/100;
			if (! $factor) {
				$factor=1;
			} 
					
			if ($iconx{$node}==0) { 
				$iconx{$node} = $xpos{$node}-$IconWidth*$factor/2;
				$icony{$node} = $ypos{$node}-$IconHeight*$factor/2;
			}

			if ($icon_transparent{$node}==0) {
				$icon_transparent{$node}= 100;
			}

			$icone2=new GD::Image($IconWidth*$factor,$IconHeight*$factor);
			$white2=$icone2->colorAllocate(255,255,255); 
			$icone2->transparent($white2);
			$icone2->copyResized($icone,0,0,0,0,$IconWidth*$factor,$IconHeight*$factor,$IconWidth,$IconHeight);
			$map->copyMerge($icone2,$iconx{$node},$icony{$node},0,0,$IconWidth*$factor,$IconHeight*$factor,$icon_transparent{$node});
		close ICON;
	} else {
		print "File \"$iconpng{$node}\" not found !!. Icon will not appear on graph\n";
	}
}

print "\nCalculating rates...\n\n" if($DEBUG);
foreach $link (keys %target){
	if ( (! $filter) || ($filter eq $group_name{$link} )) {
		$outrate=(int(($output{$link}/$maxbytesout{$link}+0.005)*100)>100) ?  100:int(($output{$link}/$maxbytesout{$link}+0.005)*100);
		$inrate=(int(($input{$link}/$maxbytesin{$link}+0.005)*100)>100) ?  100:int(($input{$link}/$maxbytesin{$link}+0.005)*100);

		if($output{$link} != 0 && $outrate == 0) { $outrate=1 }
		if($input{$link} != 0 && $inrate == 0) { $inrate=1 }
	
		print "$target{$link}: in=$input{$link}/$maxbytesin{$link} out=$output{$link}/$maxbytesout{$link}\n" if($DEBUG);
		print "Maxbytesin($link)=$maxbytesin{$link} Maxbytesout($link)=$maxbytesout{$link}\n" if($DEBUG);
		print "$target{$link}: outrate=$outrate%, inrate=$inrate%\n" if($DEBUG);
		print "$target{$link}: outrate=".(($output{$link}*100)/$maxbytesout{$link}).", inrate=".(($input{$link}*100)/$maxbytesin{$link})."\n" if($DEBUG);

		$width=$LINKWIDTH;
		# Display first arrow from node A to node B
			if ($internodes{$link}) { 
					if ($arrow_type{$link} eq "dot") {
						if ( ($GD::VERSION > 2.0) ) {
							if ($internodes{$link}==1) {
								&draw_arrow_dot(
									$xpos{$nodea{$link}}, $ypos{$nodea{$link}},
									$internodex{$link}{$internodes{$link}},$internodey{$link}{$internodes{$link}},
									$width, 0,1, &select_color($outrate), $outrate);
								&draw_arrow_dot(
									$xpos{$nodea{$link}}, $ypos{$nodea{$link}},
									$internodex{$link}{$internodes{$link}},$internodey{$link}{$internodes{$link}},
									$width, 0, 0, $black, $outrate);
							} else {
								&draw_dot(
									$xpos{$nodea{$link}}, $ypos{$nodea{$link}},
									$internodex{$link}{1},$internodey{$link}{1},
									$width, 0,1, &select_color($outrate), $outrate);
								&draw_dot(
									$xpos{$nodea{$link}}, $ypos{$nodea{$link}},
									$internodex{$link}{1},$internodey{$link}{1},
									$width, 0, 0, $black, $outrate);
								for ($i=1; $i<floor($internodes{$link}/2);$i++) {
									&draw_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										$internodex{$link}{$i+1},$internodey{$link}{$i+1},
										$width, 0,1, &select_color($outrate), $outrate);
									&draw_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										$internodex{$link}{$i+1},$internodey{$link}{$i+1},
										$width, 0, 0, $black, $outrate);
								}
								if ($internodes{$link} % 2) {
                                    # Draw arrow to middle internode								
									&draw_arrow_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										$internodex{$link}{ceil($internodes{$link}/2)},$internodey{$link}{ceil($internodes{$link}/2)},
										$width, 0,1, &select_color($outrate), $outrate);
									&draw_arrow_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										$internodex{$link}{ceil($internodes{$link}/2)},$internodey{$link}{ceil($internodes{$link}/2)},
										$width, 0, 0, $black, $outrate);
								} else {
                                    # Draw arrow to middle of central internodes
									&draw_arrow_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										middle($internodex{$link}{$i},$internodex{$link}{$i+1}),
										middle($internodey{$link}{$i},$internodey{$link}{$i+1}),
										$width, 0,1, &select_color($outrate), $outrate);
									&draw_arrow_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										middle($internodex{$link}{$i},$internodex{$link}{$i+1}),
										middle($internodey{$link}{$i},$internodey{$link}{$i+1}),
										$width, 0, 0, $black, $outrate);
								}
							}
						}
					} else {
						if ($internodes{$link}==1) {
							&draw_arrow(
								$xpos{$nodea{$link}},
								$ypos{$nodea{$link}},
								$internodex{$link}{$internodes{$link}},
								$internodey{$link}{$internodes{$link}},
								$width, 1, &select_color($outrate), $outrate);
							&draw_arrow(
								$xpos{$nodea{$link}},
								$ypos{$nodea{$link}},
								$internodex{$link}{$internodes{$link}},
								$internodey{$link}{$internodes{$link}},
								$width, 0, $black, $outrate);
						} else {
							&draw_rectangle(
								$xpos{$nodea{$link}},
								$ypos{$nodea{$link}},
								$internodex{$link}{1},
								$internodey{$link}{1},
								$width, 1, &select_color($outrate), $outrate);
							&draw_rectangle(
								$xpos{$nodea{$link}},
								$ypos{$nodea{$link}},
								$internodex{$link}{1},
								$internodey{$link}{1},
								$width, 0, $black, $outrate);
								
							for ($i=1; $i<floor($internodes{$link}/2);$i++) {
								&draw_rectangle(
									$internodex{$link}{$i},$internodey{$link}{$i},
									$internodex{$link}{$i+1},$internodey{$link}{$i+1},
									$width, 1, &select_color($outrate), $outrate);
								&draw_rectangle(
									$internodex{$link}{$i},$internodey{$link}{$i},
									$internodex{$link}{$i+1},$internodey{$link}{$i+1},
									$width, 0, $black, $outrate);
							}

							if ($internodes{$link} % 2) {
                                # Draw arrow to middle internode								
								&draw_arrow(
									$internodex{$link}{$i},$internodey{$link}{$i},
									$internodex{$link}{ceil($internodes{$link}/2)},$internodey{$link}{ceil($internodes{$link}/2)},
									$width,1, &select_color($outrate), $outrate);
								&draw_arrow(
										$internodex{$link}{$i},$internodey{$link}{$i},
										$internodex{$link}{ceil($internodes{$link}/2)},$internodey{$link}{ceil($internodes{$link}/2)},
										$width,0, $black, $outrate);
								} else {
									# Draw arrow to middle of central internodes
									&draw_arrow(
										$internodex{$link}{$i},$internodey{$link}{$i},
										middle($internodex{$link}{$i},$internodex{$link}{$i+1}),
										middle($internodey{$link}{$i},$internodey{$link}{$i+1}),
										$width,1, &select_color($outrate), $outrate);
									&draw_arrow(
										$internodex{$link}{$i},$internodey{$link}{$i},
										middle($internodex{$link}{$i},$internodex{$link}{$i+1}),
										middle($internodey{$link}{$i},$internodey{$link}{$i+1}),
										$width, 0, $black, $outrate);
							}
							
						}

					}


				&label(
					&middle($xpos{$nodea{$link}},$internodex{$link}{1}),
					&middle($ypos{$nodea{$link}},$internodey{$link}{1}),
					$outrate . "%", 0);

					if ($displayvalue{$link}) {
						if ($output{$link} >=125000) { 
							$coefdisplay=8/(1000*1000);
							$unitdisplay="Mbits";
						} else {
							$coefdisplay=8/1000;
							$unitdisplay="Kbits";
						}

						$todisplay=sprintf ("%.1f",$output{$link}*$coefdisplay). "$unitdisplay";

						&label(&middle($xpos{$nodea{$link}},$internodex{$link}{1}),
						&middle($ypos{$nodea{$link}},$internodey{$link}{1})+15,
						"$todisplay", 0);
					} 
			} else {
					# If no internodes are defined
					if ($arrow_type{$link} eq "dot") {
						if ( ($GD::VERSION > 2.0) ) {
							&draw_arrow_dot(
								$xpos{$nodea{$link}}, $ypos{$nodea{$link}},
								&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}}),
								&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}}),
								$width, 0,1, &select_color($outrate), $outrate);
							&draw_arrow_dot(
								$xpos{$nodea{$link}}, $ypos{$nodea{$link}},
								&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}}),
								&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}}),
								$width, 0,0, $black, $outrate);
						}
					} else {
							&draw_arrow(
								$xpos{$nodea{$link}}, $ypos{$nodea{$link}},
								&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}}),
								&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}}),
								$width,1, &select_color($outrate), $outrate);
							&draw_arrow(
								$xpos{$nodea{$link}}, $ypos{$nodea{$link}},
								&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}}),
								&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}}),
								$width, 0, $black, $outrate);
					}
					
					#&label(&middle($xpos{$nodea{$link}},&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}})),
					#	&middle($ypos{$nodea{$link}},&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}})),
					#	$outrate . "%", 0);
					
					if ($displayvalue{$link}) {
						if ($output{$link} >=125000) { 
							$coefdisplay=8/(1000*1000);
							$unitdisplay="Mbits";
						} else {
							$coefdisplay=8/1000;
							$unitdisplay="Kbits";
						}

						$todisplay=sprintf ("%.1f",$output{$link}*$coefdisplay). "$unitdisplay";

						&label(&middle($xpos{$nodea{$link}},&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}})),
							&middle($ypos{$nodea{$link}},&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}}+70)),
							"$todisplay", 0);
					}
			}

		# Display second arrow from node B to node A
			if ($internodes{$link}) { 
					if ($arrow_type{$link} eq "dot") {
						if ( ($GD::VERSION > 2.0) ) {
							if ($internodes{$link}==1) {
								&draw_arrow_dot(
									$xpos{$nodeb{$link}}, $ypos{$nodeb{$link}},
									$internodex{$link}{$internodes{$link}},$internodey{$link}{$internodes{$link}},
									$width, 0,1, &select_color($inrate), $inrate);
								&draw_arrow_dot(
									$xpos{$nodeb{$link}}, $ypos{$nodeb{$link}},
									$internodex{$link}{$internodes{$link}},$internodey{$link}{$internodes{$link}},
									$width, 0, 0, $black, $inrate);
							} else {
								&draw_dot(
									$xpos{$nodeb{$link}}, $ypos{$nodeb{$link}},
									$internodex{$link}{$internodes{$link}},$internodey{$link}{$internodes{$link}},
									$width, 0,1, &select_color($inrate), $inrate);
								&draw_dot(
									$xpos{$nodeb{$link}}, $ypos{$nodeb{$link}},
									$internodex{$link}{$internodes{$link}},$internodey{$link}{$internodes{$link}},
									$width, 0, 0, $black, $inrate);
								for ($i=$internodes{$link}; $i>ceil($internodes{$link}/2)+1;$i--) {
									&draw_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										$internodex{$link}{$i-1},$internodey{$link}{$i-1},
										$width, 0,1, &select_color($inrate), $inrate);
									&draw_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										$internodex{$link}{$i-1},$internodey{$link}{$i-1},
										$width, 0, 0, $black, $inrate);
								}
								if ($internodes{$link} % 2) {
                                    # Draw arrow to middle internode								
									&draw_arrow_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										$internodex{$link}{ceil($internodes{$link}/2)},$internodey{$link}{ceil($internodes{$link}/2)},
										$width, 0,1, &select_color($inrate), $inrate);
									&draw_arrow_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										$internodex{$link}{ceil($internodes{$link}/2)},$internodey{$link}{ceil($internodes{$link}/2)},
										$width, 0, 0, $black, $inrate);
								} else {
                                   # Draw arrow to middle of central internodes
									&draw_arrow_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										middle($internodex{$link}{$i},$internodex{$link}{$i-1}),
										middle($internodey{$link}{$i},$internodey{$link}{$i-1}),
										$width, 0,1, &select_color($inrate), $inrate);
									&draw_arrow_dot(
										$internodex{$link}{$i},$internodey{$link}{$i},
										middle($internodex{$link}{$i},$internodex{$link}{$i-1}),
										middle($internodey{$link}{$i},$internodey{$link}{$i-1}),
										$width, 0, 0, $black, $inrate);
								}
							}
						}
					} else {
						if ($internodes{$link}==1) {
							&draw_arrow(
								$xpos{$nodeb{$link}},
								$ypos{$nodeb{$link}},
								$internodex{$link}{$internodes{$link}},
								$internodey{$link}{$internodes{$link}},
								$width, 1, &select_color($inrate), $inrate);
							&draw_arrow(
								$xpos{$nodeb{$link}},
								$ypos{$nodeb{$link}},
								$internodex{$link}{$internodes{$link}},
								$internodey{$link}{$internodes{$link}},
								$width, 0, $black, $inrate);
						} else {
							&draw_rectangle(
								$xpos{$nodeb{$link}},
								$ypos{$nodeb{$link}},
								$internodex{$link}{$internodes{$link}},
								$internodey{$link}{$internodes{$link}},
								$width, 1, &select_color($inrate), $inrate);
							&draw_rectangle(
								$xpos{$nodeb{$link}},
								$ypos{$nodeb{$link}},
								$internodex{$link}{$internodes{$link}},
								$internodey{$link}{$internodes{$link}},
								$width, 0, $black, $inrate);
								
							for ($i=$internodes{$link}; $i>ceil($internodes{$link}/2)+1;$i--) {
								&draw_rectangle(
									$internodex{$link}{$i},$internodey{$link}{$i},
									$internodex{$link}{$i-1},$internodey{$link}{$i-1},
									$width, 1, &select_color($inrate), $inrate);
								&draw_rectangle(
									$internodex{$link}{$i},$internodey{$link}{$i},
									$internodex{$link}{$i-1},$internodey{$link}{$i-1},
									$width, 0, $black, $inrate);
							}

							if ($internodes{$link} % 2) {
                                # Draw arrow to middle internode								
								&draw_arrow(
									$internodex{$link}{$i},$internodey{$link}{$i},
									$internodex{$link}{ceil($internodes{$link}/2)},$internodey{$link}{ceil($internodes{$link}/2)},
									$width,1, &select_color($inrate), $inrate);
								&draw_arrow(
										$internodex{$link}{$i},$internodey{$link}{$i},
										$internodex{$link}{ceil($internodes{$link}/2)},$internodey{$link}{ceil($internodes{$link}/2)},
										$width,0, $black, $inrate);
								} else {
									# Draw arrow to middle of central internodes
									&draw_arrow(
										$internodex{$link}{$i},$internodey{$link}{$i},
										middle($internodex{$link}{$i},$internodex{$link}{$i-1}),
										middle($internodey{$link}{$i},$internodey{$link}{$i-1}),
										$width,1, &select_color($inrate), $inrate);
									&draw_arrow(
										$internodex{$link}{$i},$internodey{$link}{$i},
										middle($internodex{$link}{$i},$internodex{$link}{$i-1}),
										middle($internodey{$link}{$i},$internodey{$link}{$i-1}),
										$width, 0, $black, $inrate);
							}

							
						}

					}

				# Display bandwidth % links from node B to node A
				#&label(
				#	&middle($xpos{$nodeb{$link}},$internodex{$link}{$internodes{$link}}),
				#	&middle($ypos{$nodeb{$link}},$internodey{$link}{$internodes{$link}}),
				#	$inrate . "%", 0);

					if ($displayvalue{$link}) {
						if ($input{$link} >=125000) { 
							$coefdisplay=8/(1000*1000);
							$unitdisplay="Mbits";
						} else {
							$coefdisplay=8/1000;
							$unitdisplay="Kbits";
						}

						$todisplay=sprintf ("%.1f",$input{$link}*$coefdisplay). "$unitdisplay";

						&label(&middle($xpos{$nodeb{$link}},$internodex{$link}{$internodes{$link}}),
						&middle($ypos{$nodeb{$link}},$internodey{$link}{$internodes{$link}})+15,
						"$todisplay", 0);
					} 
			} else {
					# If no internodes are defined
					if ($arrow_type{$link} eq "dot") {
						if ( ($GD::VERSION > 2.0) ) {
							&draw_arrow_dot(
								$xpos{$nodeb{$link}}, $ypos{$nodeb{$link}},
								&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}}),
								&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}}),
								$width, 0,1, &select_color($inrate), $inrate);
							&draw_arrow_dot(
								$xpos{$nodeb{$link}}, $ypos{$nodeb{$link}},
								&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}}),
								&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}}),
								$width, 0,0, $black, $inrate);
						}
					} else {
							&draw_arrow(
								$xpos{$nodeb{$link}}, $ypos{$nodeb{$link}},
								&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}}),
								&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}}),
								$width,1, &select_color($inrate), $inrate);
							&draw_arrow(
								$xpos{$nodeb{$link}}, $ypos{$nodeb{$link}},
								&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}}),
								&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}}),
								$width, 0, $black, $inrate);
					}
					
					#&label(&middle($xpos{$nodeb{$link}},&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}})),
					#	&middle($ypos{$nodeb{$link}},&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}})),
					#	$inrate . "%", 0);
					
					if ($displayvalue{$link}) {
						if ($input{$link} >=125000) { 
							$coefdisplay=8/(1000*1000);
							$unitdisplay="Mbits";
						} else {
							$coefdisplay=8/1000;
							$unitdisplay="Kbits";
						}

						$todisplay=sprintf ("%.1f",$input{$link}*$coefdisplay). "$unitdisplay";

						&label(&middle($xpos{$nodeb{$link}},&middle($xpos{$nodea{$link}},$xpos{$nodeb{$link}})),
							&middle($ypos{$nodeb{$link}},&middle($ypos{$nodea{$link}},$ypos{$nodeb{$link}}+70)),
							"$todisplay", 0);
					}
			}
		

	 if ($internodedisplay{$link}) {
		for ($i=1; $i<=($internodes{$link}); $i++) {
			$gdinternode=&draw_internode($i,$FONT,$black,$white);
			$map->copyMerge(
				$gdinternode,
				$internodex{$link}{$i}-($FONT->width*length($i)),$internodey{$link}{$i}-($FONT->height)/2,
				0,0,
				($gdinternode->width),($gdinternode->height),
				$internodedisplay{$link}
			);
		}
	}

	}
}

print "\n" if($DEBUG);

foreach(keys %xpos){
	if (length($label{$_}) >0) {
	 	&label($xpos{$_},$ypos{$_},$label{$_}, 3);
 		#&label($xpos{$_},$ypos{$_},"$xpos{$_} - $ypos{$_}", 3);
	}
}



&annotation;

# print image...
print "Generating image file $OUTPUTFILE...\n\n" if($DEBUG);
open(PNG,">$OUTPUTFILE")||die("$OUTPUTFILE: $!\n");
if ( $^O eq 'MSWin32' )
{
    binmode ( PNG ) ;
}

print PNG $map->png;
close PNG;

# hint, resizing the image could make it look better

exit;


# print labels
sub label{
	my($xpos,$ypos,$label,$pad)=@_;
	my($strwidth)=$FONT->width*length($label);
	my($strheight)=$FONT->height;
	$map->filledRectangle(
		$xpos-$strwidth/2-$pad-2, $ypos-$strheight/2-$pad+1,
		$xpos+$strwidth/2+$pad+1, $ypos+$strheight/2+$pad,
		$black);
	$map->filledRectangle(
		$xpos-$strwidth/2-$pad-1, $ypos-$strheight/2-$pad+2,
		$xpos+$strwidth/2+$pad, $ypos+$strheight/2+$pad-1,
		$white);
	$map->string($FONT,
		$xpos-$strwidth/2, $ypos-$strheight/2+1,
		$label, $black)
}


# print annotation
sub annotation{
	my($title)="Traffic load";
       $strwidth=gdLargeFont->width*length($label{$_});
	$strheight=gdLargeFont->height;

	#$t=localtime(time);
	$t=strftime "%e %b %Y - %H\:%M\:%S", localtime($DATE);
	#$t=localtime($DATE);
	#$t=$DATE;
	#$t=gmtime(time);

	if (gdSmallFont->width*length("Last updated on $t")>gdLargeFont->width*length($titlegraph)) {
		$titlewidth=gdSmallFont->width*length("Last updated on $t");
	} else {
		$titlewidth=gdLargeFont->width*length($titlegraph);
	}

	#$map->filledRectangle($titlexpos+1, $titleypos+1, $titlexpos+$titlewidth+3, $titleypos+gdLargeFont->height*2+3, $titlebackground);

	#$map->rectangle($titlexpos-5, $titleypos-3, $titlexpos+$titlewidth+10, $titleypos+gdLargeFont->height*2+6, $titleforeground);


	$map->string(gdLargeFont, $titlexpos+2, $titleypos+2, $titlegraph, $titleforeground);
	$map->string(gdSmallFont, $titlexpos+2, $titleypos+20, " Last updated on $t", $titleforeground);

	#$map->filledRectangle($keyxpos,$keyypos,
	#	$keyxpos+gdLargeFont->width*length($title)+10,
	#	$keyypos+gdLargeFont->height*($scales+1)+gdTinyFont->height*2.5,
	#	$black);
		
	#$map->filledRectangle($keyxpos,$keyypos,
	#	$keyxpos+gdLargeFont->width*length($title)+10,
	#	$keyypos+gdLargeFont->height*($scales+1)+10,
	#	$gray);
	#$map->rectangle($keyxpos,$keyypos,
	#	$keyxpos+gdLargeFont->width*length($title)+10,
	#	$keyypos+gdLargeFont->height*($scales+1)+gdTinyFont->height*2.5,
	#	$black);

	#$map->string(gdLargeFont,
	#	$keyxpos+4,
	#	$keyypos+4,
	#	"Traffic load",  $black);

	#my($i)=1;
	#foreach(sort {$scale_low{$a}<=>$scale_low{$b}} keys %scale_low){
	#	$map->filledRectangle(
	#		$keyxpos+6,
	#		$keyypos+gdLargeFont->height*$i+8,
	#		$keyxpos+6+16,
	#		$keyypos+gdLargeFont->height*$i+gdLargeFont->height+6,
	#		$color{$_});
	#	$map->string(gdLargeFont,
	#		$keyxpos+6+20,
	#		$keyypos+gdLargeFont->height*$i+8,
	#		"$scale_low{$_}-$scale_high{$_}%", $black);
#			"$color{$_} $scale_low{$_}-$scale_high{$_}%", $black);
	#	$i++
	#}
	#$map->string(gdTinyFont,$keyxpos+2,$keyypos+gdLargeFont->height*$i+8,"Weathermap4RRD $VERSION",$black);
	#$map->string(
	#gdTinyFont,
	#$keyxpos+(((gdLargeFont->width)*length($title)+10)-((gdTinyFont->width)*length("Weathermap4RRD $VERSION")))/2+2,
	#$keyypos+gdLargeFont->height*($i)+11,
	#"Weathermap4RRD $VERSION",
	#$white);
}

sub select_color {
	my($rate)=($_[0]>100) ? 100:$_[0];
	if($rate=="0"){return($white)}
	foreach(sort {$scale_high{$a}<=>$scale_high{$b}} keys %scale_high){
		if($scale_low{$_}<=$rate && $rate<=$scale_high{$_}){
			return($color{$_});
		}
	}
}

sub autoscale {
	my($autoscale_div,$start_red,$start_green,$start_blue,$end_red,$end_green,$end_blue)=($_[0],$_[1],$_[2],$_[3],$_[4],$_[5],$_[6]);

	if (!$autoscale_div) { $autoscale_div=7; }
	#print "autoscale=$autoscale_div\n";	

	$dif_red=-($start_red-$end_red);
	$dif_green=-($start_green-$end_green);
	$dif_blue=-($start_blue-$end_blue);

	$step_red=$dif_red/$autoscale_div;
	$step_green=$dif_green/$autoscale_div;
	$step_blue=$dif_blue/$autoscale_div;

	$bounder_inf=0;
	$bounder_sup=int(100/$autoscale_div);

	for ($i=0; $i<$autoscale_div; $i++) {
		$scale_low{"$bounder_inf:$bounder_sup"}=$bounder_inf;
		$scale_high{"$bounder_inf:$bounder_sup"}=$bounder_sup;
		$scale_red{"$bounder_inf:$bounder_sup"}=$start_red+$i*$step_red;
		$scale_green{"$bounder_inf:$bounder_sup"}=$start_green+$i*$step_green;
		$scale_blue{"$bounder_inf:$bounder_sup"}=$start_blue+$i*$step_blue;
		$bounder_inf=$bounder_sup;
		if ( $i == ($autoscale_div-2)) {
			$bounder_sup=100;
		} else {
			$bounder_sup=($i+2)*int(100/$autoscale_div);
		}
	}

}

sub alloc_colors {

	if ( ($white=$map->colorAllocate(255,255,255)) =="-1") {
		$white=$map->colorClosest(255,255,255);
		print "**** Warning ****\n";
		print "Background picture is using a 8-bit indexed palette. Unable to allocate new color to palette.\n";
		print "Colors needed by Weathermap4rrd will be based on existing colors. Few of them could be bad displayed.\n";
		print "To get right color displayed, you should convert background picture to 24-bit truecolor mode.\n";
		print "********\n";
	}

	if ( ($black=$map->colorAllocate(0,0,0)) =="-1") {
		$black=$map->colorClosest(0,0,0);
	}

	if ( ($gray=$map->colorAllocate(248,248,248)) =="-1") {
		$gray=$map->colorClosest(248,248,248);
	}
	
	if (($red=$map->colorAllocate(255,0,0)) =="-1") {
		$red=$map->colorClosest(255,0,0);
	}
	if (($green=$map->colorAllocate(64,255,128)) =="-1") {
		$green=$map->colorClosest(64,255,128);
	}
	if (($darkgray=$map->colorAllocate(128,128,128)) =="-1") {
		$darkgray=$map->colorClosest(128,128,128);
	}
	
	if (($titlebackground=$map->colorAllocate($titlebackground_red,$titlebackground_green,$titlebackground_blue)) =="-1") {
		$titlebackground=$map->colorClosest($titlebackground_red,$titlebackground_green,$titlebackground_blue);
	}
	if (($titleforeground=$map->colorAllocate($titleforeground_red,$titleforeground_green,$titleforeground_blue)) =="-1") {
		$titleforeground=$map->colorClosest($titleforeground_red,$titleforeground_green,$titleforeground_blue);
	}

	foreach(keys %scale_red){
		if (($color{$_} = $map->colorAllocate($scale_red{$_},$scale_green{$_},$scale_blue{$_})) =="-1" ) {
		$color{$_} = $map->colorClosest($scale_red{$_},$scale_green{$_},$scale_blue{$_});
		}
	}
}


sub read_config {
my($config)=shift;
my($node,$link);

print "\nReading configuration file...\n\n" if($DEBUG);

$scales=0;
open(CONF,$config) or die "$config: $!\n";
while(<CONF>){
	if(/^\s*BACKGROUND\s+(\S+)/i){
		if(-s "$1"){
			$background=$1;
			print "found BACKGROUND: $background\n" if($DEBUG);
		}
	}

	if(/^\s*FONT\s+(\S+)/i){
		if("$1" ne ""){
			@FONTLIST=(gdTinyFont,gdSmallFont,gdMediumBoldFont,gdLargeFont,gdGiantFont);
			$FONT=$FONTLIST[$1-1];
			print "found FONT: $FONT\n" if($DEBUG);
		}
	}
	
	if(/^\s*CNT_WIDTH_ARROW_BASE\s+(\d+)/i){
		if("$1" ne ""){
			$CNT_WIDTH_ARROW_BASE=$1;
			print "found CNT_WIDTH_ARROW_BASE: $CNT_WIDTH_ARROW_BASE\n" if($DEBUG);
		}
	}

	if(/^\s*WIDTH\s+(\d+)/i){
		if("$1" ne ""){
			$WIDTH=$1;
			print "found WIDTH: $WIDTH\n" if($DEBUG);
		}
	}
	if(/^\s*HEIGHT\s+(\d+)/i){
		if("$1" ne ""){
			$HEIGHT=$1;
			print "found HEIGHT: $HEIGHT\n" if($DEBUG);
		}
	}
	if(/^\s*NODE\s+(\S+)/i){
		$node=$1;
		print "found NODE: $node\n" if($DEBUG);
	}
	if(/^\s*POSITION\s+(\d+)\s+(\d+)/i){
		$xpos{$node}=$1;
		$ypos{$node}=$2;
		print "found NODE: $node XPOS: $xpos{$node} YPOS: $xpos{$node}\n" if($DEBUG);
	}
	if(/^\s*LABEL\s+(\S+)/i){
		$label{$node}=$1;
		print "found NODE: $node LABEL: $label{$node}\n" if($DEBUG);
	}

	if(/^\s*ICONRESIZE\s+(\d+)/i){
		$iconresize{$node}=$1;
		print "found ICONRESIZE: $node ICONRESIZE: $iconresize{$node}\n" if($DEBUG);
	}

	if(/^\s*ICON\s+(\S+)/i){
		$iconpng{$node}=$1;
		print "found ICON: $node ICON: $iconpng{$node}\n" if($DEBUG);
	}

	if(/^\s*ICONPOS\s+(\d+)\s+(\d+)/i){
		$iconx{$node}=$1;
		$icony{$node}=$2;
		print "found ICONPOS: $node ICONPOS x: $iconx{$node}\n" if($DEBUG);
		print "found ICONPOS: $node ICONPOS y: $icony{$node}\n" if($DEBUG);
	}

	if(/^\s*ICONTPT\s+(\d+)/i){
		$icon_transparent{$node}=$1;
		print "found ICONTPT: $node ICONTPT: $icon_transparent{$node}\n" if($DEBUG);
	}

	if(/^\s*LINK\s+(\S+)/i){
		$link=$1;
		print "found LINK: $link\n" if($DEBUG);
	}

	if(/^\s*LINKWIDTH\s+(\S+)/i){
		$LINKWIDTH=$1;
		print "found LINKWIDTH: $LINKWIDTH\n" if($DEBUG);
	}

	if(/^\s*NODES\s+(\S+)\s+(\S+)/i){
		$nodea{$link}=$1;
		$nodeb{$link}=$2;
		print "found LINK: $link NODEA: $nodea{$link} NODEB: $nodeb{$link}\n" if($DEBUG);
	}

	if(/^\s*ARROW\s+(\S+)/i){
		$arrow_type{$link}=$1;
		print "found ARROW: $link ARROW: $arrow_type{$link}\n" if($DEBUG);
	}

	if(/^\s*GROUP\s+(\S+)/i){
		$group_name{$link}=$1;
		print "found GROUP: $link GROUP: $group_name{$link}\n" if($DEBUG);
	}


	if(/^\s*TARGET\s+(\S+)/i){
		$target{$link}=$1;
		print "found LINK: $link TARGET: $target{$link}\n" if($DEBUG);
	}


	# If only one value is set for bandwidth. IN=OUT bandwidth.
	if(/^\s*BANDWIDTH\s+(\d+)/i){
		    $bandwidth{$link}=$1;
			$maxbytesin{$link}=$bandwidth{$link}*1000/8;
			$maxbytesout{$link}=$maxbytesin{$link};
			print "found LINK: $link BANDWIDTH: $bandwidth{$link}\n" if($DEBUG);
	}

	if(/^\s*BANDWIDTH\s+(\S+)\s+(\S+)/i){
	        $bandwidthin{$link}=$1;
			$maxbytesin{$link}=$bandwidthin{$link}*1000/8;
			$bandwidthout{$link}=$2;
			$maxbytesout{$link}=$bandwidthout{$link}*1000/8;
			print "found LINK: $link BANDWIDTH IN: $bandwidthin{$link} BANDWIDTH OUT: $bandwidthout{$link}\n" if($DEBUG);
	}


	if(/^\s*WIDTH\s+(\d+)/i){
		$WIDTH=$1;
		print "found LINK: WIDTH : $WIDTH\n" if($DEBUG);
	}

	if(/^\s*HEIGHT\s+(\d+)/i){
		$HEIGHT=$1;
		print "found LINK: HEIGHT : $HEIGHT\n" if($DEBUG);
	}

	
	if(/^\s*OUTPUTFILE\s+(\S+)/i){
		$OUTPUTFILE=$1;
		print "found OUTPUTFILE: $OUTPUTFILE\n" if($DEBUG);
	}


	if(/^\s*UNIT\s+(\S+)/i){
		$unit{$link}=$1;
		if ( $unit{$link} eq "Mbits" ) {
			$coef{$link}=1000*1000/8;
		}
		if ( $unit{$link} eq "Kbits" ) {
			$coef{$link}=1000/8;
		}

		if ( $unit{$link} eq "bits" ) {
			$coef{$link}=1/8;
		}

		if ( $unit{$link} eq "Mbytes" ) {
			$coef{$link}=1024*1024;
		}

		if ( $unit{$link} eq "Kbytes" ) {
			$coef{$link}=1024;
		}

		if ( $unit{$link} eq "bytes" ) {
			$coef{$link}=1;
		}
		print "found LINK: $link COEF: $coef{$link}\n" if($DEBUG);
	}

	if(/^\s*INPOS\s+(\d+)/i){
		$inpos{$link}=$1;
		print "found LINK: $link INPOS : $inpos{$link}\n" if($DEBUG);
	}
	if(/^\s*OUTPOS\s+(\d+)/i){
		$outpos{$link}=$1;
		print "found LINK: $link OUTPOS : $outpos{$link}\n" if($DEBUG);
	}
	if(/^\s*DISPLAYVALUE\s+(\d+)/i){
		$displayvalue{$link}=$1;
		print "found LINK: $link DISPLAYVALUE : $displayvalue{$link}\n" if($DEBUG);
	}
	
	if(/^\s*TITLE\s+\"(.+)\"/i){
		$titlegraph="$1";
		print "found LINK: $link TITLE : --$titlegraph--\n" if($DEBUG);
	}

	if(/^\s*KEYPOS\s+(\d+)\s+(\d+)/i){
		$keyxpos=$1;
		$keyypos=$2;
		print "found KEY POSITION: $keyxpos $keyypos\n" if($DEBUG);
	}

	
	if(/^\s*TITLEPOS\s+(\d+)\s+(\d+)/i){
		$titlexpos=$1;
		$titleypos=$2;
		print "found TITLE POSITION: $titlexpos $titleypos\n" if($DEBUG);
	}

	if(/^\s*TITLEBACKGROUND\s+(\d+)\s+(\d+)\s+(\d+)/i){
		$titlebackground_red=$1;
		$titlebackground_green=$2;
		$titlebackground_blue=$3;
		print "found TITLE BACKGROUND: $titlebackground_red $titlebackground_green $titlebackground_blue\n" if($DEBUG);
	}

	if(/^\s*TITLEFOREGROUND\s+(\d+)\s+(\d+)\s+(\d+)/i){
		$titleforeground_red=$1;
		$titleforeground_green=$2;
		$titleforeground_blue=$3;
		print "found TITLE FOREGROUND: $titleforeground_red $titleforeground_green $titleforeground_blue\n" if($DEBUG);
	}

	if(/^\s*AUTOSCALE\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/i){
		$autoscale=1;
		$autoscale_div=$1;
		$scales=$autoscale_div;
		autoscale($autoscale_div,$2,$3,$4,$5,$6,$7);
		print "found AUTOSCALE: $link AUTOSCALE: $autoscale\n" if($DEBUG);
	}

	if( (/^\s*AUTOSCALE\s+(\d+)/i) && (!$autoscale)){
		$autoscale=1;
		$autoscale_div=$1;
		$scales=$autoscale_div;
		autoscale($autoscale_div,24,232,2,233,28,1);
		print "found AUTOSCALE: $link AUTOSCALE: $autoscale\n" if($DEBUG);
	}

	if(/^\s*INTERNODE\s+(\d+)\s+(\d+)/i){
		$internodes{$link}++;
		$internodex{$link}{$internodes{$link}}=$1;
		$internodey{$link}{$internodes{$link}}=$2;
		print "found INTERNODE : $link INTERNODE $internodes{$link} position $internodex{$link}{$internodes{$link}} $internodey{$link}{$internodes{$link}}\n" if($DEBUG);
	}

	if(/^\s*INTERNODEDISPLAY\s+(\d+)/i){
		$internodedisplay{$link}=$1;
		print "found INTERNODEDISPLAY : $link INTERNODEDISPLAY ".$internodedisplay{$link}." directive detected.\n" if($DEBUG);
	}


	if(/^\s*SCALE\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)/i){
		if ($autoscale) {
			if (!$warn_autoscale) {	print "Warning : AUTOSCALE directive used. Your own SCALE values won't be used.\n"; }
			$warn_autoscale=1;
		} else {
			$scale_low{"$1:$2"}=$1;
			$scale_high{"$1:$2"}=$2;
			$scale_red{"$1:$2"}=$3;
			$scale_green{"$1:$2"}=$4;
			$scale_blue{"$1:$2"}=$5;
			$scales++;
			print "found SCALE DATA: $1:$2 $3:$4:$5\n" if($DEBUG);
		}
	}
}
print "\n" if($DEBUG);
}


sub middle{
	return int( $_[0] + ($_[1]-$_[0])/2 )
}

sub dist{
	return int( sqrt( $_[0]*$_[0] + $_[1]*$_[1] ) )
}

sub newx{
	my($a,$b,$x,$y)=@_;
	return int( cos( atan2($y,$x) + atan2($b,$a) ) * sqrt( $x*$x + $y*$y ) );
}

sub newy{
	my($a,$b,$x,$y)=@_;
	return int( sin( atan2($y,$x) + atan2($b,$a) ) * sqrt( $x*$x + $y*$y ) );
}

sub dist_bw_points{
	my($x1,$y1,$x2,$y2)=($_[0],$_[1],$_[2],$_[3]);
	return int(sqrt(($x2-$x1)*($x2-$x1)+($y2-$y1)*($y2-$y1)));
}

sub getposy_line {
	my($x,$x1,$y1,$x2,$y2)=($_[0],$_[1],$_[2],$_[3],$_[4]);
    $a=($y2-$y1)/($x2-$x1);
	$b=$y1-$a*$x1;

	return int($a*$x+$b);
}

sub getposx_line {
	my($y,$x1,$y1,$x2,$y2)=($_[0],$_[1],$_[2],$_[3],$_[4]);
	$c=($x2-$x1)/($y2-$y1);
	$d=$x1-$c*$y1;
	return int($c*$y+$d);
}
						

sub draw_rectangle {
	my($x1,$y1,$x2,$y2,$w,$solid,$color,$out)=($_[0],$_[1],$_[2],$_[3],$_[4],$_[5],$_[6],$_[7]);
	my($arrow)=new GD::Polygon;
	my($base_arrow)=$out/20;
	#if ($base_arrow<1 || $CNT_WIDTH_ARROW_BASE == 1) { $base_arrow=1 }
	$base_arrow=1;

	$arrow->addPt(
		$x1 + &newx($x2-$x1, $y2-$y1, 0, $base_arrow*$w),
		$y1 + &newy($x2-$x1, $y2-$y1, 0, $base_arrow*$w)
		);

	$arrow->addPt(
		$x2 + &newx($x2-$x1, $y2-$y1, 0, $w),
		$y2 + &newy($x2-$x1, $y2-$y1, 0, $w)
		);

	$arrow->addPt(
		$x2 + &newx($x2-$x1, $y2-$y1, 0, -$w),
		$y2 + &newy($x2-$x1, $y2-$y1, 0, -$w)
		);

	$arrow->addPt(
		$x1 + &newx($x2-$x1, $y2-$y1, 0, -$base_arrow*$w),
		$y1 + &newy($x2-$x1, $y2-$y1, 0, -$base_arrow*$w)
		);

	if($solid){
		$map->filledPolygon($arrow,$color);
	}else{
		$map->polygon($arrow,$color);
	}
}

sub draw_arrow {
	my($x1,$y1,$x2,$y2,$w,$solid,$color,$out)=($_[0],$_[1],$_[2],$_[3],$_[4],$_[5],$_[6],$_[7]);
	my($arrow)=new GD::Polygon;
	my($base_arrow)=$out/20;
	#if ($base_arrow<1 || $CNT_WIDTH_ARROW_BASE == 1) { $base_arrow=1 }
	$base_arrow=1;

	$arrow->addPt(
		$x1 + &newx($x2-$x1, $y2-$y1, 0, $base_arrow*$w),
		$y1 + &newy($x2-$x1, $y2-$y1, 0, $base_arrow*$w)
		);

	$arrow->addPt(
		$x2 + &newx($x2-$x1, $y2-$y1, -4*$w, $w),
		$y2 + &newy($x2-$x1, $y2-$y1, -4*$w, $w)
		);

	$arrow->addPt(
		$x2 + &newx($x2-$x1, $y2-$y1, -4*$w, 2*$w),
		$y2 + &newy($x2-$x1, $y2-$y1, -4*$w, 2*$w)
		);

	$arrow->addPt( $x2, $y2);

	$arrow->addPt(
		$x2 + &newx($x2-$x1, $y2-$y1, -4*$w, -2*$w),
		$y2 + &newy($x2-$x1, $y2-$y1, -4*$w, -2*$w)
		);

	$arrow->addPt(
		$x2 + &newx($x2-$x1, $y2-$y1, -4*$w, -$w),
		$y2 + &newy($x2-$x1, $y2-$y1, -4*$w, -$w)
		);

	$arrow->addPt(
		$x1 + &newx($x2-$x1, $y2-$y1, 0, -$base_arrow*$w),
		$y1 + &newy($x2-$x1, $y2-$y1, 0, -$base_arrow*$w)
		);

	if($solid){
		$map->filledPolygon($arrow,$color);
	}else{
		$map->polygon($arrow,$color);
	}
}

sub draw_internode{
	my ($string,$font,$textcolor,$bgcolor)=($_[0],$_[1],$_[2],$_[3]);

	$radius=7;
	$pix_width=2*$radius;
	$pix_height=2*$radius;

	$inter = new GD::Image ($pix_width+2,$pix_height+2);
	$whiteinter=$inter->colorAllocate(255, 255, 255);
	$inter->transparent($whiteinter);
	$blackinter=$inter->colorAllocate(0,0,0);
	$redinter=$inter->colorAllocate(255,0,0);
	$blueinter=$inter->colorAllocate(0,0,255);
	$yellowinter=$inter->colorAllocate(255,255,0);
	
	$inter->filledEllipse($radius+1, $radius+1,2*$radius,2*$radius,$blueinter);
	$inter->ellipse($radius+1, $radius+1,2*$radius,2*$radius,$blackinter);
	$width=gdTinyFont->width*length($string);
	$inter->string(gdTinyFont, $radius-1, $radius-$width/2, $string, $yellowinter);

	return ($inter);
	
}

sub draw_dot{
	my($x1,$y1,$x2,$y2,$w,$step,$solid,$color,$out)=($_[0],$_[1],$_[2],$_[3],$_[4],$_[5],$_[6],$_[7],$_[8]);
	
	$start_rayon=$w;
	$rayon=$w;
	
	$dif_horizontal=abs($x1-$x2);
	$dif_vertical=abs($y1-$y2);
			
	if ($dif_horizontal>$dif_vertical) {
		if ( ($x1 < $x2) ) {
			for ($xi = $x1+$start_rayon; (dist_bw_points($xi,$yi,$x2,$y2)>2*$w) ; $xi=$xi+$last_rayon+$rayon+$step) {
					$yi=getposy_line($xi,$x1,$y1,$x2,$y2);
				if ($solid) {
					$map->filledEllipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				} else {
					$map->ellipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				}
				$last_rayon=$rayon;

				if (($CNT_WIDTH_ARROW_BASE == 0) && ($start_rayon!=$w) && ($rayon>$w)) {
					$rayon=$start_rayon*(dist_bw_points($xi,$yi,$x2,$y2)/dist_bw_points($x1,$y1,$x2,$y2)); 
				}
			}
		} else {
			for ($xi = $x1-$start_rayon; dist_bw_points($xi,$yi,$x2,$y2)>2*$w; $xi=$xi-($last_rayon+$rayon)-$step) {
				$yi=getposy_line($xi,$x1,$y1,$x2,$y2);
				if ($solid) {
					$map->filledEllipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				} else {
					$map->ellipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				}
				$last_rayon=$rayon;
				if (($CNT_WIDTH_ARROW_BASE == 0) && ($start_rayon!=$w) && ($rayon>$w)) {
					$rayon=$start_rayon*(dist_bw_points($xi,$yi,$x2,$y2)/dist_bw_points($x1,$y1,$x2,$y2)); 
				}
			}
		}
	} else {
		if ( ($y1<$y2) ) {
			for ($yi = $y1+$start_rayon; dist_bw_points($xi,$yi,$x2,$y2)>2*$w; $yi=$yi+$last_rayon+$rayon+$step) {
				$xi=getposx_line($yi,$x1,$y1,$x2,$y2);
				if ($solid) {
					$map->filledEllipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				} else {
					$map->ellipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				}
				$last_rayon=$rayon;

				if (($CNT_WIDTH_ARROW_BASE == 0) && ($start_rayon!=$w) && ($rayon>$w)) {
					$rayon=$start_rayon*(dist_bw_points($xi,$yi,$x2,$y2)/dist_bw_points($x1,$y1,$x2,$y2)); 
				}
			}
		} else {
			for ($yi = $y1-$start_rayon; dist_bw_points($xi,$yi,$x2,$y2)>2*$w; $yi=$yi-($last_rayon+$rayon)-$step) {
				$xi=getposx_line($yi,$x1,$y1,$x2,$y2);
				if ($solid) {
					$map->filledEllipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				} else {
					$map->ellipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				}
				$last_rayon=$rayon;

				if (($CNT_WIDTH_ARROW_BASE == 0) && ($start_rayon!=$w) && ($rayon>$w)) {
					$rayon=$start_rayon*(dist_bw_points($xi,$yi,$x2,$y2)/dist_bw_points($x1,$y1,$x2,$y2)); 
				}

			}
		}
	}
}


sub draw_arrow_dot{
	my($x1,$y1,$x2,$y2,$w,$step,$solid,$color,$out)=($_[0],$_[1],$_[2],$_[3],$_[4],$_[5],$_[6],$_[7],$_[8]);
	
	$start_rayon=$w;
	$rayon=$w;
	
	$dif_horizontal=abs($x1-$x2);
	$dif_vertical=abs($y1-$y2);
			
	if ($dif_horizontal>$dif_vertical) {
		if ( ($x1 < $x2) ) {
			for ($xi = $x1+$start_rayon; (dist_bw_points($xi,$yi,$x2,$y2)>4*$w) ; $xi=$xi+$last_rayon+$rayon+$step) {
					$yi=getposy_line($xi,$x1,$y1,$x2,$y2);
				if ($solid) {
					$map->filledEllipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				} else {
					$map->ellipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				}
				$last_rayon=$rayon;

				if (($CNT_WIDTH_ARROW_BASE == 0) && ($start_rayon!=$w) && ($rayon>$w)) {
					$rayon=$start_rayon*(dist_bw_points($xi,$yi,$x2,$y2)/dist_bw_points($x1,$y1,$x2,$y2)); 
				}
			}
		} else {
			for ($xi = $x1-$start_rayon; dist_bw_points($xi,$yi,$x2,$y2)>4*$w; $xi=$xi-($last_rayon+$rayon)-$step) {
				$yi=getposy_line($xi,$x1,$y1,$x2,$y2);
				if ($solid) {
					$map->filledEllipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				} else {
					$map->ellipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				}
				$last_rayon=$rayon;
				if (($CNT_WIDTH_ARROW_BASE == 0) && ($start_rayon!=$w) && ($rayon>$w)) {
					$rayon=$start_rayon*(dist_bw_points($xi,$yi,$x2,$y2)/dist_bw_points($x1,$y1,$x2,$y2)); 
				}
			}
		}
	} else {
		if ( ($y1<$y2) ) {
			for ($yi = $y1+$start_rayon; dist_bw_points($xi,$yi,$x2,$y2)>4*$w; $yi=$yi+$last_rayon+$rayon+$step) {
				$xi=getposx_line($yi,$x1,$y1,$x2,$y2);
				if ($solid) {
					$map->filledEllipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				} else {
					$map->ellipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				}
				$last_rayon=$rayon;

				if (($CNT_WIDTH_ARROW_BASE == 0) && ($start_rayon!=$w) && ($rayon>$w)) {
					$rayon=$start_rayon*(dist_bw_points($xi,$yi,$x2,$y2)/dist_bw_points($x1,$y1,$x2,$y2)); 
				}
			}
		} else {
			for ($yi = $y1-$start_rayon; dist_bw_points($xi,$yi,$x2,$y2)>4*$w; $yi=$yi-($last_rayon+$rayon)-$step) {
				$xi=getposx_line($yi,$x1,$y1,$x2,$y2);
				if ($solid) {
					$map->filledEllipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				} else {
					$map->ellipse($xi,$yi,2*$rayon, 2*$rayon,$color);
				}
				$last_rayon=$rayon;

				if (($CNT_WIDTH_ARROW_BASE == 0) && ($start_rayon!=$w) && ($rayon>$w)) {
					$rayon=$start_rayon*(dist_bw_points($xi,$yi,$x2,$y2)/dist_bw_points($x1,$y1,$x2,$y2)); 
				}

			}
		}
	}
	my($arrow)=new GD::Polygon;

	$arrow->addPt(
		$x2 + &newx($x2-$x1, $y2-$y1, -4*$w, $w),
		$y2 + &newy($x2-$x1, $y2-$y1, -4*$w, $w)
		);

	$arrow->addPt(
		$x2 + &newx($x2-$x1, $y2-$y1, -4*$w, 2*$w),
		$y2 + &newy($x2-$x1, $y2-$y1, -4*$w, 2*$w)
		);

	$arrow->addPt( $x2, $y2);

	$arrow->addPt(
		$x2 + &newx($x2-$x1, $y2-$y1, -4*$w, -2*$w),
		$y2 + &newy($x2-$x1, $y2-$y1, -4*$w, -2*$w)
		);

	$arrow->addPt(
		$x2 + &newx($x2-$x1, $y2-$y1, -4*$w, -$w),
		$y2 + &newy($x2-$x1, $y2-$y1, -4*$w, -$w)
		);

	if($solid){
		$map->filledPolygon($arrow,$color);
	}else{
		$map->polygon($arrow,$color);
	}

}
sub rrdtool_getversion() {
	$version=`$RRDTOOL_PATH/rrdtool | grep tobi\@oetiker.ch |cut -d" " -f2`;
	($major, $majorsub, $minorsub)= split(/\./, $version);
	return ($major.".".$majorsub);
}

sub version {
        print <<EOM;
Wearthermap4RRD v$VERSION - http://weathermap4rrd.tropicalex.net
EOM
}

sub usage {
        print <<EOM;
Wearthermap4RRD v$VERSION - http://weathermap4rrd.tropicalex.net
based on Network Weathermap v$VERSION 
Usage: $0 [OPTION]...

 -c, --config=FILE  configuration file (default $CONFIG)
 -o, --output=FILE  output image file default (default $OUTPUTFILE)
     --date "dd/mm/yyyy hh:mm" (default "now")
 -g, --group=GROUPNAME  display only links belonging to specified GROUPNAME (display all links by default)
 -v, --version      print version
 -h, --help         print this text
 -d, --debug        enable debug output

EOM
}
