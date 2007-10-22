<?php
// RRDtool datasource plugin.
//     gauge:filename.rrd:ds_in:ds_out
//     filename.rrd:ds_in:ds_out
//     filename.rrd:ds_in:ds_out
//
class WeatherMapDataSource_rrd extends WeatherMapDataSource {

	function Init(&$map)
	{
		#if (extension_loaded('RRDTool')) // fetch the values via the RRDtool Extension
		#{
	#		debug("RRD DS: Using RRDTool php extension.\n");
#			return(TRUE);
#		}
#		else
#		{
			if (file_exists($map->rrdtool)) {
				if((function_exists('is_executable')) && (!is_executable($map->rrdtool)))
				{
					warn("RRD DS: RRDTool exists but is not executable? [WMRRD01]\n");
					return(FALSE);
				}
				$map->rrdtool_check="FOUND";
				return(TRUE); 
			}
			// normally, DS plugins shouldn't really pollute the logs
			// this particular one is important to most users though...
			if($map->context=='cli')
			{
				warn("RRD DS: Can't find RRDTOOL. Check line 29 of the 'weathermap' script.\nRRD-based TARGETs will fail. [WMRRD02]\n");
			}
			if($map->context=='cacti')
			{    // unlikely to ever occur
				warn("RRD DS: Can't find RRDTOOL. Check your Cacti config. [WMRRD03]\n");
			}
#		}

		return(FALSE);
	}

	function Recognise($targetstring)
	{
		if(preg_match("/^(.*\.rrd):([\-a-zA-Z0-9_]+):([\-a-zA-Z0-9_]+)$/",$targetstring,$matches))
		{
			return TRUE;
		}
		elseif(preg_match("/^(.*\.rrd)$/",$targetstring,$matches))
		{
			return TRUE;
		}
		else
		{
			return FALSE;
		}
	}

	// Actually read data from a data source, and return it
	// returns a 3-part array (invalue, outvalue and datavalid time_t)
	// invalue and outvalue should be -1,-1 if there is no valid data
	// data_time is intended to allow more informed graphing in the future
	function ReadData($targetstring, &$map, &$item)
	{
		$in_ds = "traffic_in";
		$out_ds = "traffic_out";
		$dsnames[IN] = "traffic_in";
		$dsnames[OUT] = "traffic_out";
		$data[IN] = 0;
		$data[OUT] = 0;
		$rrdfile = $targetstring;

		$multiplier = 8;

		$inbw=-1;
		$outbw=-1;
		$data_time = 0;

		if(preg_match("/^(.*\.rrd):([\-a-zA-Z0-9_]+):([\-a-zA-Z0-9_]+)$/",$targetstring,$matches))
		{
			$in_ds = $matches[2];
			$out_ds = $matches[3];
			$rrdfile = $matches[1];
			
			$dsnames[IN] = $matches[2];
			$dsnames[OUT] = $matches[3];
			
			debug("Special DS names seen (".$dsnames[IN]." and ".$dsnames[OUT].").\n");
		}

		if(preg_match("/^rrd:(.*)/",$rrdfile,$matches))
		{
			$rrdfile = $matches[1];
		}

		if(preg_match("/^gauge:(.*)/",$rrdfile,$matches))
		{
			$rrdfile = $matches[1];
			$multiplier = 1;
		}

                if(preg_match("/^scale:(\d*\.?\d*):(.*)/",$rrdfile,$matches)) 
                {
                        $rrdfile = $matches[2];
                        $multiplier = $matches[1];
                }

		// we get the last 800 seconds of data - this might be 1 or 2 lines, depending on when in the
		// cacti polling cycle we get run. This ought to stop the 'some lines are grey' problem that some
		// people were seeing


// NEW PLAN - READ LINES (LIKE NOW), *THEN* CHECK IF REQUIRED DS NAMES EXIST (AND FAIL IF NOT),
//     *THEN* GET THE LAST LINE WHERE THOSE TWO DS ARE VALID, *THEN* DO ANY PROCESSING.
//  - this allows for early failure, and also tolerance of empty data in other parts of an rrd (like smokeping uptime)

		if(file_exists($rrdfile))
		{
			debug ("RRD ReadData: Target DS names are $in_ds and $out_ds\n");

			$period = intval($map->get_hint('rrd_period'));
			if($period == 0) $period = 800;
			$start = $map->get_hint('rrd_start');
			if($start == '') {
			    $start = "now-$period";
			    $end = "now";
			}
			else
			{
			    $end = "start+".$period;
			}

			$values=array();

			if ((1==0) && extension_loaded('RRDTool')) // fetch the values via the RRDtool Extension
			{
				// for the php-rrdtool module, we use an array instead...
				$rrdparams = array("AVERAGE","--start",$start,"--end",$end);
				$rrdreturn = rrd_fetch ($rrdfile,$rrdparams,count($rrdparams));
				print_r($rrdreturn);
				// XXX - figure out what to do with the results here
				$now = $rrdreturn['start'];
				$n=0;
				do {
					$now += $rrdreturn['step'];
					print "$now - ";
					for($i=0;$i<$rrdreturn['ds_cnt'];$i++)
					{
						print $rrdreturn['ds_namv'][$i] . ' = '.$rrdreturn['data'][$n++]." ";
					}
					print "\n";
				} while($now <= $rrdreturn['end']);
					
			}
			else
			{

				# $command = '"'.$map->rrdtool . '" fetch "'.$rrdfile.'" AVERAGE --start '.$start.' --end '.$end;
				$command=$map->rrdtool . " fetch $rrdfile AVERAGE --start $start --end $end";

				debug ("RRD ReadData: Running: $command\n");
				$pipe=popen($command, "r");
				
				$lines=array ();
				$count = 0;
				$linecount = 0;

				if (isset($pipe))
				{
					$headings=fgets($pipe, 4096);
					// this replace fudges 1.2.x output to look like 1.0.x
					// then we can treat them both the same.
					$heads=preg_split("/\s+/", preg_replace("/^\s+/","timestamp ",$headings) );
				
					fgets($pipe, 4096); // skip the blank line
					$buffer='';

					while (!feof($pipe))
					{
						$line=fgets($pipe, 4096);
						debug ("> " . $line);
						$buffer.=$line;
						$lines[]=$line;
						$linecount++;
					}				
					pclose ($pipe);
					
					debug("RRD ReadData: Read $linecount lines from rrdtool\n");
					debug("RRD ReadData: Headings are: $headings\n");

					if( (in_array($in_ds,$heads) || $in_ds == '-') && (in_array($out_ds,$heads) || $out_ds == '-') )
					{
					    // deal with the data, starting with the last line of output
					     $rlines=array_reverse($lines);
		     
					     foreach ($rlines as $line)
					     {
						 debug ("--" . $line . "\n");
						 $cols=preg_split("/\s+/", $line);
						 for ($i=0, $cnt=count($cols)-1; $i < $cnt; $i++) { 
							$h = $heads[$i];
							$v = $cols[$i];
							# print "|$h|,|$v|\n";
							$values[$h] = trim($v); 
						}
		 
						$data_ok=FALSE;
		 
						foreach (array(IN,OUT) as $dir)
						{
							$n = $dsnames[$dir];
							# print "|$n|\n";
							if(array_key_exists($n,$values))
							{
								$candidate = $values[$n];
								if(preg_match('/^\d+\.?\d*e?[+-]?\d*:?$/i', $candidate))
								{
									$data[$dir] = $candidate * $multiplier;
									debug("$candidate is OK value for $n\n");
									$data_ok = TRUE;
								}
							}
						}
						
						if($data_ok)
						{
							// at least one of the named DS had good data
							$data_time = intval($values['timestamp']);	
							// break out of the loop here   
							break;
						}
					     }
					}
					else
					{
					    // report DS name error
					     $names = join(",",$heads);
						warn("RRD ReadData: Neither of your DS names ($in_ds & $out_ds) were found, even though there was a valid data line. Maybe they are wrong? Valid DS names in this file are: $names [WMRRD06]\n");
					}
		   
				}
				else
				{
					warn("RRD ReadData: failed to open pipe to RRDTool: ".$php_errormsg." [WMRRD04]\n");
				}
			}
		
		}
		else
		{
			warn ("Target $rrdfile doesn't exist. Is it a file? [WMRRD06]\n");
		}

		$inbw = $data[IN];
		$outbw = $data[OUT];

		debug ("RRD ReadData: Returning ($inbw,$outbw,$data_time)\n");

		return( array($inbw, $outbw, $data_time) );
	}
}

// vim:ts=4:sw=4:
?>
