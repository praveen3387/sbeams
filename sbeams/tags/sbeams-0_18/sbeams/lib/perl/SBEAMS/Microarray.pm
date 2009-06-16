package SBEAMS::Microarray;

###############################################################################
# Program     : SBEAMS::Microarray
# Author      : Eric Deutsch <edeutsch@systemsbiology.org>
# $Id$
#
# Description : Perl Module to handle all SBEAMS-MicroArray specific items.
#
###############################################################################


use strict;
use vars qw($VERSION @ISA $sbeams);
use CGI::Carp qw(fatalsToBrowser croak);

use SBEAMS::Microarray::DBInterface;
use SBEAMS::Microarray::HTMLPrinter;
use SBEAMS::Microarray::TableInfo;
use SBEAMS::Microarray::Settings;

@ISA = qw(SBEAMS::Microarray::DBInterface
          SBEAMS::Microarray::HTMLPrinter
          SBEAMS::Microarray::TableInfo
          SBEAMS::Microarray::Settings);


###############################################################################
# Global Variables
###############################################################################
$VERSION = '0.02';


###############################################################################
# Constructor
###############################################################################
sub new {
    my $this = shift;
    my $class = ref($this) || $this;
    my $self = {};
    bless $self, $class;
    return($self);
}


###############################################################################
# Receive the main SBEAMS object
###############################################################################
sub setSBEAMS {
    my $self = shift;
    $sbeams = shift;
    return($sbeams);
}


###############################################################################
# Provide the main SBEAMS object
###############################################################################
sub getSBEAMS {
    my $self = shift;
    return($sbeams);
}


###############################################################################

1;

__END__
###############################################################################
###############################################################################
###############################################################################