<?php

$guest_account = true;

chdir('../../');
include_once("./include/auth.php");
include_once("./include/config.php");

// include the weathermap class so that we can get the version
include_once(dirname(__FILE__)."/Weathermap.class.php");

$action = "";
if (isset($_POST['action'])) {
	$action = $_POST['action'];
} else if (isset($_GET['action'])) {
	$action = $_GET['action'];
}

switch($action)
{
case 'viewmapcycle':
	include_once($config["base_path"]."/include/top_graph_header.php");
	print "<div id=\"overDiv\" style=\"position:absolute; visibility:hidden; z-index:1000;\"></div>\n";
	print "<script type=\"text/javascript\" src=\"overlib.js\"><!-- overLIB (c) Erik Bosrup --></script> \n";
	weathermap_fullview(TRUE);
	weathermap_versionbox();

	include_once($config["base_path"]."/include/bottom_footer.php");
	break;

case 'viewmap':
	include_once($config["base_path"]."/include/top_graph_header.php");
	print "<div id=\"overDiv\" style=\"position:absolute; visibility:hidden; z-index:1000;\"></div>\n";
	print "<script type=\"text/javascript\" src=\"overlib.js\"><!-- overLIB (c) Erik Bosrup --></script> \n";

	if( isset($_REQUEST['id']) && is_numeric($_REQUEST['id']) )
	{
		weathermap_singleview($_REQUEST['id']);
	}
	weathermap_versionbox();

	include_once($config["base_path"]."/include/bottom_footer.php");
	break;
default:
	include_once($config["base_path"]."/include/top_graph_header.php");
	print "<div id=\"overDiv\" style=\"position:absolute; visibility:hidden; z-index:1000;\"></div>\n";
	print "<script type=\"text/javascript\" src=\"overlib.js\"><!-- overLIB (c) Erik Bosrup --></script> \n";

	if(read_config_option("weathermap_pagestyle") == 0)
	{
		weathermap_thumbview();
	}
	if(read_config_option("weathermap_pagestyle") == 1)
	{
		weathermap_fullview();
	}

	weathermap_versionbox();
	include_once($config["base_path"]."/include/bottom_footer.php");
	break;
}


function weathermap_cycleview()
{

}

function weathermap_singleview($mapid)
{
	global $colors;

	$outdir = dirname(__FILE__).'/output/';
	$confdir = dirname(__FILE__).'/configs/';

// $map = db_fetch_assoc("select * from weathermap_maps where id=".$mapid);
	$map = db_fetch_assoc("select weathermap_maps.* from weathermap_auth,weathermap_maps where weathermap_maps.id=weathermap_auth.mapid and active='on' and (userid=".$_SESSION["sess_user_id"]." or userid=0) and weathermap_maps.id=".$mapid);

	if(sizeof($map))
	{
		$htmlfile = $outdir."weathermap_".$map[0]['id'].".html";
		$maptitle = $map[0]['titlecache'];
		if($maptitle == '') $maptitle= "Map for config file: ".$map[0]['configfile'];

		html_graph_start_box(1,true);
?>
<tr bgcolor="<?php print $colors["panel"];?>">
  <td>
	  <table width="100%" cellpadding="0" cellspacing="0">
		<tr>
		   <td class="textHeader" nowrap><?php print $maptitle; ?></td>
		</tr>
	  </table>
  </td>
</tr>
<?php
//  print "<tr><td><h2>".$maptitle."</h2></td></tr>";
		print "<tr><td>";

		if(file_exists($htmlfile))
		{
			include($htmlfile);
		}
		else
		{
			print "<div align=\"center\" style=\"padding:20px\"><em>This map hasn't been created yet.";

			global $config, $user_auth_realms, $user_auth_realm_filenames;
			$realm_id2 = 0;

			if (isset($user_auth_realm_filenames[basename('weathermap-cacti-plugin.php')])) {
				$realm_id2 = $user_auth_realm_filenames[basename('weathermap-cacti-plugin.php')];
			}

			if ((db_fetch_assoc("select user_auth_realm.realm_id from user_auth_realm where user_auth_realm.us
				er_id='" . $_SESSION["sess_user_id"] . "' and user_auth_realm.realm_id='$realm_id2'")) || (empty($realm_id2))) {

					print " (If this message stays here for more than one poller cycle, then check your cacti.log file for errors!)";

				}
			print "</em></div>";
		}
		print "</td></tr>";
		html_graph_end_box();

	}
}

function weathermap_show_manage_tab()
{
	global $config, $user_auth_realms, $user_auth_realm_filenames;
	$realm_id2 = 0;

	if (isset($user_auth_realm_filenames['weathermap-cacti-plugin-mgmt.php'])) {
		$realm_id2 = $user_auth_realm_filenames['weathermap-cacti-plugin-mgmt.php'];
	}
	if ((db_fetch_assoc("select user_auth_realm.realm_id from user_auth_realm where user_auth_realm.user_id='" . $_SESSION["sess_user_id"] . "' and user_auth_realm.realm_id='$realm_id2'")) || (empty($realm_id2))) {

		print '<a href="' . $config['url_path'] . 'plugins/weathermap/weathermap-cacti-plugin-mgmt.php">Manage Maps</a>';
	}
}

function weathermap_thumbview()
{
	global $colors;

	$maplist = db_fetch_assoc( "select distinct weathermap_maps.* from weathermap_auth,weathermap_maps where weathermap_maps.id=weathermap_auth.mapid and active='on' and (userid=".$_SESSION["sess_user_id"]." or userid=0) order by sortorder, id");


	if(sizeof($maplist) == 1)
	{
		$pagetitle = "Network Weathermap";
		weathermap_fullview();
	}
	else
	{
		$pagetitle = "Network Weathermaps";

		html_graph_start_box(2,true);
?>
<tr bgcolor="<?php print $colors["panel"];?>">
				<td>
						<table width="100%" cellpadding="0" cellspacing="0">
								<tr>
								   <td class="textHeader" nowrap> <?php print $pagetitle; ?></td>
				<td align="right"> <a href="?action=viewmapcycle">automatically cycle</a> between full-size maps) </td>
				</tr>
			</table>
		</td>
</tr>
<tr>
<td><i>Click on thumbnails for a full view (or you can <a href="?action=viewmapcycle">automatically cycle</a> between full-size maps)</i></td>
</tr>
<?php
		html_graph_end_box();

		$i = 0;
		if (sizeof($maplist) > 0)
		{

			$outdir = dirname(__FILE__).'/output/';
			$confdir = dirname(__FILE__).'/configs/';

			$imageformat = strtolower(read_config_option("weathermap_output_format"));

			html_graph_start_box(1,true);
			print "<tr><td>";
			foreach ($maplist as $map) {
				$i++;

				$thumbfile = $outdir."weathermap_thumb_".$map['id'].".".$imageformat;
				$thumburl = "output/weathermap_thumb_".$map['id'].".".$imageformat;
				$maptitle = $map['titlecache'];
				if($maptitle == '') $maptitle= "Map for config file: ".$map['configfile'];

				print '<div class="wm_thumbcontainer" style="margin: 2px; border: 1px solid #bbbbbb; padding: 2px; float:left;">';
				if(file_exists($thumbfile))
				{
					print '<div class="wm_thumbtitle" style="font-size: 1.2em; font-weight: bold; text-align: center">'.$maptitle.'</div><a href="weathermap-cacti-plugin.php?action=viewmap&id='.$map['id'].'"><img class="wm_thumb" src="'.$thumburl.'" alt="'.$maptitle.'" border="0" hspace="5" vspace="5" title="'.$maptitle.'"/></a>';
				}
				else
				{
					print "(thumbnail for map ".$map['id']." not created yet)";
				}
				print '</div> ';
			}
			print "</td></tr>";
			html_graph_end_box();

		}
		else
		{
			print "<div align=\"center\" style=\"padding:20px\"><em>You Have No Maps</em></div>\n";
		}
	}
}

function weathermap_fullview($cycle=FALSE)
{
	global $colors;

	$_SESSION['custom']=false;

	$maplist = db_fetch_assoc( "select distinct weathermap_maps.* from weathermap_auth,weathermap_maps where weathermap_maps.id=weathermap_auth.mapid and active='on' and (userid=".$_SESSION["sess_user_id"]." or userid=0) order by sortorder, id");
	html_graph_start_box(2,true);

	if(sizeof($maplist) == 1)
	{
		$pagetitle = "Network Weathermap";
	}
	else
	{
		$pagetitle = "Network Weathermaps";
	}

?>
<tr bgcolor="<?php print $colors["panel"];?>">
				<td>
						<table width="100%" cellpadding="0" cellspacing="0">
								<tr>
								   <td class="textHeader" nowrap> <?php print $pagetitle; ?> </td>
				<td align="right">
				<?php if(! $cycle) { ?>
				<a href="?action=viewmapcycle">automatically cycle</a> between full-size maps)
				<?php } else { ?>
				Cycling all available maps. <a href="?action=">Stop.</a>
				<?php }?>
				</td>
				</tr>
			</table>
		</td>
</tr>
<?php
	html_graph_end_box();

	$i = 0;
	if (sizeof($maplist) > 0)
	{

		$outdir = dirname(__FILE__).'/output/';
		$confdir = dirname(__FILE__).'/configs/';
		foreach ($maplist as $map)
		{
			$i++;
			$htmlfile = $outdir."weathermap_".$map['id'].".html";
			$maptitle = $map['titlecache'];
			if($maptitle == '') $maptitle= "Map for config file: ".$map['configfile'];

			print '<div class="weathermapholder" id="mapholder_'.$map['id'].'">';
			html_graph_start_box(1,true);
?>
		<tr bgcolor="#<?php print $colors["header_panel"];?>">
				<td colspan="3">
						<table width="100%" cellspacing="0" cellpadding="3" border="0">
								<tr>
										<td align="left" class="textHeaderDark"><a name="map_<?php echo $map['id']; ?>"></a>
									 <?php print htmlspecialchars($maptitle); ?>
				</td>
								</tr>
						</table>
				</td>
		</tr>
	<tr>
		<td>
<?php

			if(file_exists($htmlfile))
			{
				include($htmlfile);
			}
			else
			{
				print "<div align=\"center\" style=\"padding:20px\"><em>This map hasn't been created yet.</em></div>";
			}

			print '</td></tr>';
			html_graph_end_box();
			print '</div>';
		}


		if($cycle)
		{
			$refreshtime = read_config_option("weathermap_cycle_refresh");
			// OK, so the Cycle plugin does all this with a <META> tag at the bottom of the body
			// that overrides the one at the top (that Cacti puts there). Unfortunately, that
			// isn't valid HTML! So here's a Javascript driven way to do it

			// It has the advantage that the image switching is cleaner, too.
			// We also do a nice thing of taking the poller-period (5 mins), and the
			// available maps, and making sure each one gets equal time in the 5 minute period.
?>
			<script type="text/javascript">

			function addEvent(obj, evType, fn)
			{
				if (obj.addEventListener)
				{
					obj.addEventListener(evType, fn, false);
					return true;
				}

				else if (obj.attachEvent)
				{
					var r = obj.attachEvent("on" + evType, fn);
					return r;
				}

				else
				{
					return false;
				}
			}

			wm_maps = new Array;
			wm_current = 0;

			function wm_tick()
			{
				document.getElementById(wm_maps[wm_current]).style.display='none';
				wm_current++;
				if(wm_current >= wm_maps.length) wm_current = 0;
				document.getElementById(wm_maps[wm_current]).style.display='block';

			}

			function wm_reload()
			{
				window.location.reload();
			}

			function wm_initJS()
			{
				var i,j;
				var possible_maps = document.getElementsByTagName('div');

				j = 0;

				for (i = 0; i < possible_maps.length; ++i)
				{
					if (possible_maps[i].className == 'weathermapholder')
					{
						wm_maps[j] = possible_maps[i].id;
						j++;
					}
				}
				// stop here if there were no maps
				if(j>0)
				{
					wm_current = 0;
					// hide all but the first one
					if(j>1)
					{
						for(i=1;i<j;i++)
						{
							document.getElementById(wm_maps[i]).style.display='none';
						}
					}
					// figure out how long the refresh is, so that we get
					// through all the maps in exactly 5 minutes

					var period = <?php echo $refreshtime ?> * 1000;

					if(period == 0)
					{
						var period = 300000/j;
					}           

					// our map-switching clock
					setInterval(wm_tick, period);
					// when to reload the whole page (with new map data)
					setTimeout( wm_reload ,300000);
				}
			}


			addEvent(window, 'load', wm_initJS);

			</script>
<?php
		}
	}
	else
	{
		print "<div align=\"center\" style=\"padding:20px\"><em>You Have No Maps</em></div>\n";
	}


}

function weathermap_versionbox()
{
	global $WEATHERMAP_VERSION, $colors;
	;
	$pagefoot = "Powered by <a href=\"http://www.network-weathermap.com/?v=$WEATHERMAP_VERSION\">PHP Weathermap version $WEATHERMAP_VERSION</a>";

	html_graph_start_box(1,true);

?>
<tr bgcolor="<?php print $colors["panel"];?>">
				<td>
						<table width="100%" cellpadding="0" cellspacing="0">
								<tr>
								   <td class="textHeader" nowrap> <?php print $pagefoot; ?> </td>
				</tr>
			</table>
		</td>
</tr>
<?php
	html_graph_end_box();
}
// vim:ts=4:sw=4:
?>
