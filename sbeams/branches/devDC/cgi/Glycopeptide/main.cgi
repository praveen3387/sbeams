#!/usr/local/bin/perl

###############################################################################
# Program     : main.cgi
# Author      : Eric Deutsch <edeutsch@systemsbiology.org>
# $Id: main.cgi 3243 2005-03-21 09:02:00Z edeutsch $
#
# Description : This script authenticates the user, and then
#               displays the opening access page.
#
# SBEAMS is Copyright (C) 2000-2005 Institute for Systems Biology
# This program is governed by the terms of the GNU General Public License (GPL)
# version 2 as published by the Free Software Foundation.  It is provided
# WITHOUT ANY WARRANTY.  See the full description of GPL terms in the
# LICENSE file distributed with this software.
#
###############################################################################


###############################################################################
# Get the script set up with everything it will need
###############################################################################
use strict;
use vars qw ($q $PROGRAM_FILE_NAME
             $current_contact_id $current_username);
use lib qw (../../lib/perl);
#use CGI;
use CGI::Carp qw(fatalsToBrowser croak);

use SBEAMS::Connection qw($q $log);
use SBEAMS::Connection::Settings;

use SBEAMS::PeptideAtlas;

use SBEAMS::Glycopeptide;
use SBEAMS::Glycopeptide::Settings;
use SBEAMS::Glycopeptide::Tables;

my $sbeams = new SBEAMS::Connection;
my $atlas = new SBEAMS::PeptideAtlas;
$atlas->setSBEAMS($sbeams);
my $glyco = new SBEAMS::Glycopeptide;
$glyco->setSBEAMS($sbeams);
my %params;
my $build_id;


###############################################################################
# Global Variables
###############################################################################
$PROGRAM_FILE_NAME = 'main.cgi';
main();


###############################################################################
# Main Program:
#
# Call $sbeams->Authentication and stop immediately if authentication
# fails else continue.
###############################################################################
sub main { 

  #### Do the SBEAMS authentication and exit if a username is not returned
  exit unless ($current_username = $sbeams->Authenticate(
  permitted_work_groups_ref=>['Glycopeptide_user','Glycopeptide_admin']));

  $sbeams->parse_input_parameters( q=>$q, parameters_ref=>\%params );
  if ( $params{unipep_build_id} ) {
    my $build_id = $glyco->get_current_build( build_id => $params{unipep_build_id} );
    if ( $build_id != $params{unipep_build_id} ) {
      $sbeams->set_page_message( type => 'Error', msg => 'You must log in to access specified build' );
    }

  }
  $build_id = $glyco->get_current_build();
  #### Print the header, do what the program does, and print footer
  $glyco->printPageHeader();
  my $intro = get_intro();
  my $content = get_content();
  print $sbeams->getGifSpacer(600);
  print $intro;

  print $content;
  $glyco->printPageFooter();

} # end main


sub get_intro {
  my $build = "<I>" . $glyco->get_current_build_name() . "</I>\n";
  my $address = 'dcampbel@systemsbiology.net';
  my $content = qq~
  <P>
  This is the main page of the Glycopeptide module, which is the internal representation of the Unipep database.  Some statistics about the current build, $build, are shown below.  
  <BR><BR>
  Comments are <A HREF='mailto:$address'>welcome!</A>
  </P>
  ~;
  return $content;
}


sub get_content {
  my $cutoff = $glyco->get_current_prophet_cutoff();
  # ALTERED from 
#  my $sql = qq~
#  SELECT identified_peptide_sequence, peptide_prophet_score
#  FROM $TBGP_IDENTIFIED_PEPTIDE
#
  

  my $sql = qq~
  SELECT observed_peptide_sequence, MAX(peptide_prophet_score)
  FROM $TBGP_OBSERVED_PEPTIDE OP 
  JOIN $TBGP_OBSERVED_TO_IPI OTI 
    ON OTI.observed_peptide_id = OP.observed_peptide_id 
  JOIN $TBGP_IPI_DATA ID 
    ON OTI.ipi_data_id = ID.ipi_data_id 
  JOIN $TBGP_UNIPEP_BUILD UB 
    ON UB.ipi_version = ID.ipi_version_id 
  WHERE unipep_build_id = $build_id
  GROUP BY observed_peptide_sequence
  ~;

  my @results = $sbeams->selectSeveralColumns( $sql );
  my %stats;
  my $cnt;
  for my $row ( @results ) {
    $cnt++;
    $stats{cnt}++;
    $stats{cys}++ if $row->[0] =~ /C/;
    my ( $missed, $tryp );
    $tryp++ if $row->[0] =~ /^[-|R|K]/;
    $tryp++ if $row->[0] =~ /[R|K]\..$/;
    $missed++ if $row->[0] =~ /^.\..*K[^P].*\..$/;
    $missed++ if $row->[0] =~ /^.\..*R[^P].*\..$/;
    $stats{notryp}++ if $tryp == 0;
    $stats{sing_tryp}++ if $tryp == 1;
    $stats{doub_tryp}++ if $tryp == 2;
    $stats{missed}++ if $missed;
    if ( $row->[1] >= $cutoff ) {
      $stats{cutcnt}++;
      $stats{cutcys}++ if $row->[0] =~ /C/;
      $stats{cutnotryp}++ if $tryp == 0;
      $stats{cutsing_tryp}++ if $tryp == 1;
      $stats{cutdoub_tryp}++ if $tryp == 2;
      $stats{cutmissed}++ if $missed;
    }
  }
  my @table = ( ['Category', "Prophet cutoff ($cutoff)", "Total" ] );
  push @table, [ 'Unique peptides:', $stats{cutcnt} . ' (' . sprintf( "%d\%", $stats{cutcnt}/$stats{cnt}*100 ) . ')', $stats{cnt} ] if $stats{cnt};
  push @table, [ 'Cysteine containing:', $stats{cutcys} . ' (' . sprintf( "%d\%", $stats{cutcys}/$stats{cys}*100 ) . ')', $stats{cys} ] if $stats{cys};
  push @table, [ 'Singly tryptic:', $stats{cutsing_tryp} . ' (' . sprintf( "%d\%", $stats{cutsing_tryp}/$stats{sing_tryp}*100 ) . ')', $stats{sing_tryp} ] if $stats{sing_tryp};
  push @table, [ 'Doubly tryptic:', $stats{cutdoub_tryp} .  ' (' . sprintf( "%d\%", $stats{cutdoub_tryp}/$stats{doub_tryp}*100 ) . ')', $stats{doub_tryp} ] if $stats{doub_tryp};
  push @table, [ 'Non tryptic:', $stats{cutnotryp} . ' (' . sprintf( "%d\%", $stats{cutnotryp}/$stats{notryp}*100 ) . ')', $stats{notryp} ] if $stats{notryp};
  push @table, [ 'Missed Cleavage:', $stats{cutmissed} . ' (' . sprintf( "%d\%", $stats{cutmissed}/$stats{missed}*100 ) . ')', $stats{missed} ] if $stats{missed};
  my $table = $atlas->encodeSectionTable( header => 1,
                                          width => 400,
                                          align => [qw(right right right)],
                                          rows => \@table );
  return "<P>$table</P>";
} # end showMainPage

