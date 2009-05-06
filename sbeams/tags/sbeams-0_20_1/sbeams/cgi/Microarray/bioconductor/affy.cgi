#!/tools/bin/perl -w

use CGI qw/:standard/;
use CGI::Pretty;
$CGI::Pretty::INDENT = "";
use FileManager;
use Batch;
use BioC;
use Site;
use strict;


use XML::LibXML;
use FindBin;

use lib "$FindBin::Bin/../../../lib/perl";
use SBEAMS::Connection qw($log $q);
use SBEAMS::Connection::Settings;
use SBEAMS::Microarray::Tables;

use SBEAMS::Microarray;
use SBEAMS::Microarray::Settings;
use SBEAMS::Microarray::Tables;
use SBEAMS::Microarray::Affy_Analysis;


use vars qw ($sbeams $affy_o $sbeamsMOD $cgi $current_username $USER_ID
  $PROG_NAME $USAGE %OPTIONS $QUIET $VERBOSE $DEBUG $DATABASE
  $TABLE_NAME $PROGRAM_FILE_NAME $CATEGORY $DB_TABLE_NAME
  @MENU_OPTIONS %CONVERSION_H);


$sbeams    = new SBEAMS::Connection;
$affy_o = new SBEAMS::Microarray::Affy_Analysis;
$affy_o->setSBEAMS($sbeams);

$sbeamsMOD = new SBEAMS::Microarray;
$sbeamsMOD->setSBEAMS($sbeams);

#### Do the SBEAMS authentication and exit if a username is not returned
	exit
	  unless (
		$current_username = $sbeams->Authenticate(
			permitted_work_groups_ref =>
			  [ 'Microarray_user', 'Microarray_admin', 'Admin' ],
			#connect_read_only=>1,
			#allow_anonymous_access=>1,
		)
	  );
# Create the global CGI instance
#our $cgi = new CGI;
#using a single cgi in instance created during authentication
$cgi = $q;

#### Read in the default input parameters
	my %parameters;
	my $n_params_found = $sbeams->parse_input_parameters(
		q              => $cgi,
		parameters_ref => \%parameters
	);

#### Process generic "state" parameters before we start
	$sbeams->processStandardParameters( parameters_ref => \%parameters );



# Create the global FileManager instance
our $fm = new FileManager;

# Handle initializing the FileManager session
if ($cgi->param('files_token') ) {
    my $token = $cgi->param('files_token') ;
	

	if ($fm->init_with_token($BC_UPLOAD_DIR, $token)) {
	    error('Upload session has no files') if !($fm->filenames > 0);
	} else {
	    error("Couldn't load session from token: ". $cgi->param('files_token')) if
	        $cgi->param('files_token');
	}
}else{
	error("Cannot start session no param 'files_token'");
}

if (! $cgi->param('step')) {
    $sbeamsMOD->printPageHeader();
	step1();
	$sbeamsMOD->printPageFooter();
    
} elsif ($cgi->param('step') == 1) {
   $sbeamsMOD->printPageHeader();
	step2();
	$sbeamsMOD->printPageFooter();
} elsif ($cgi->param('step') == 2) {
    step3();
} else {
    error('There was an error in form input.');
}

#### Subroutine: step1
# Make step 1 form
####
sub step1 {

	#print $cgi->header;    
	#site_header('Affymetrix Expression Analysis: affy');
	
	print h1('Affymetrix Expression Analysis: affy'),
	      h2('Step 1:'),
	      start_form,
	      hidden('step', 1),
	      p('Enter upload manager token:', textfield('token', $fm->token, 30)),
	      p('Enter number of CEL files:', textfield('numfiles', '', 10)),
	      submit("Next Step"),
	      end_form,
	      p(a({-href=>"upload.cgi"}, "Go to Upload Manager"));

    print <<'END';
<h2>Quick Help</h2>

<p>
affy performs low-level analysis of Affymetrix data and calculates
expression summaries for each of the probe sets. It processes the
data in three main stages: background correction, normalization,
and summarization. There are a number of different methods that
can be used for each of those stages. affy can also be configured
to handle PM-MM correction in several different ways.
</p>

<p>
To get started with affy, first upload all of your CEL files with
the upload manager. Make sure to note your upload manager token.
Next you must specify the number of CEL files to process. Generally,
you should process all the CEL files for an experiment at once, to
take maximum advantage of cross-chip normalization.
</p>
END
	
	site_footer();
}

#### Subroutine: step2
# Handle step 1, make step 2 form
####
sub step2 {
	
	my $numfiles = $cgi->param('numfiles');
	my %labels;
	
	if (grep(/[^0-9]|^$/, $numfiles) || !($numfiles > 0)) {
	    error('Please enter an integer greater than 0.');
	}

	 site_header('Affymetrix Expression Analysis: affy');
	
	
	print h1('Affymetrix Expression Analysis: affy'),
	      h2('Step 2:'),
	      start_form, 
	      hidden('files_token', $fm->token),
	      hidden(-name=>'step', -default=>2, -override=>1),
	      hidden(-name=>'normalization_token', -value=>$cgi->param('normalization_token')),
	      hidden(-name=>'analysis_id', -value=>$cgi->param('analysis_id')),
	      hidden('numfiles', $cgi->param('numfiles')),
	      p("Select files for expression analysis:");
	      
	print '<table>',
	      Tr(th('#'), th('File'), th('Sample Name'));
	
	
	for (my $i = 0; $i < $numfiles; $i++) {
	    my $sample_name = $cgi->param("file$i");
	    $sample_name =~ s/\.CEL$//;	#Remove the .CEL suffix to make a nice sample name
	    
	    print Tr(td($i+1),
	             td({-bgcolor=>"#CCCCCC"},
	             	$cgi->textfield(-name=>"file$i",
                            -default=>$cgi->param("file$i"),
                            -override=>1,
                            -size=>40,
                            -onFocus=>"this.blur()" )),
	             
	             td(textfield('sampleNames', $sample_name, 40)));
	}
	
	print '</table>',
		  p("Choose the processing method:"),
		  p($cgi->radio_group('process', ['RMA','GCRMA'], 'RMA','true')),
		  "---- or ----",
		  p($cgi->radio_group('process', ['Custom'], '-')),
		  '<ul><table>',
		  Tr(td({-style=>"text-align: right"}, "Background Correction:"), 
		     td(popup_menu('custom', ['none', 'rma', 'rma2', 'mas' ], 'rma'))),
		  Tr(td({-style=>"text-align: right"}, "Normalization:"),
		     td(popup_menu('custom', ['quantiles', 'quantiles.robust', 'loess', 'contrasts', 'constant', 'invariantset', 'qspline', 'vsn'], 'quantiles'))),
		  Tr(td({-style=>"text-align: right"}, "PM Correction:"),
		     td(popup_menu('custom', ['mas', 'pmonly', 'subtractmm'], 'pmonly'))),
		  Tr(td({-style=>"text-align: right"}, "Summarization:"),
		     td(popup_menu('custom', ['avgdiff', 'liwong', 'mas', 'medianpolish', 'playerout', 'rlm'], 'medianpolish'))),
		  '</table></ul>',
		  p($cgi->checkbox('log2trans','checked','YES','Log base 2 transform the results (required for multtest)')),
		  #p($cgi->checkbox('fmcopy','checked','YES','Copy exprSet back to the upload manager for further analysis')),
		  p("E-mail address where you would like your job status sent: (optional)", br(), textfield('email', '', 40)),
	      p(submit("Submit Job")),
	      end_form;
	
    print <<'END';
<h2>Quick Help</h2>

<p>
For information about each of the processing methods, see Ben
Bolstad's PDF vignette, <a
href="http://www.bioconductor.org/repository/devel/vignette/builtinMethods.pdf">affy:
Built-in Processing Methods</a>. Not all of the methods work with
one another so consult that document first.
</p>

<p>
Variance Stabilization (vsn) is a background correction and
normalization method written as an add-on to affy. If you use it,
make sure to set background correction to "none" as vsn already
does this. For more information, see Wolfgang Huber's PDF vignette,
<a
href="http://www.bioconductor.org/repository/devel/vignette/vsn.pdf">Robust
calibration and variance stabilization with VSN</a>.
</p>

<p>
GCRMA is an expression measure developed by Zhijin Wu and Rafael
A. Irizarry.  It pools MM probes with similar GC content to form
a pseudo-MM suitable for background correction of those probe pairs.
To use GCRMA, select either gcrma-eb or gcrma-mle for Background
Correction and rlm for Summarization. For further information,
please see their paper currently under preparation, <a
href="http://www.biostat.jhsph.edu/~ririzarr/papers/gcpaper.pdf">A
Model Based Background Adjustement for Oligonucleotide Expression
Arrays</a>.  Also, please note that the gcrma R package is currenly
a developmental version.
</p>
END
	
	site_footer();
}

#### Subroutine: step3
# Handle step 2, redirect web browser to results
####
sub step3 {
	my $jobname = '';
	
	
	if ($cgi->param('normalization_token') ){
		$jobname = $cgi->param('normalization_token');
		#print STDERR "FOUND NORM TOKEN '$jobname'<br>";
	}else{
		$jobname = "affy-norm" . rand_token();	
	}
	my (@filenames, $script, $output, $jobsummary, $custom, $error, $args, $job);
	my @custom = $cgi->param('custom');
	
	for (my $i = 0; $i < $cgi->param('numfiles'); $i++) {
		my $debug = $fm->path();
		error("File does not exist.") if !$fm->file_exists($cgi->param("file$i"));
			
		$filenames[$i] = $cgi->param("file$i");
	}
	
	if ($cgi->param('email') && !check_email($cgi->param('email'))) {
		error("Invalid e-mail address.");
	}
	
	if ($cgi->param('process') eq "Custom" && !expresso_safe(@custom)) {
	    error("Invalid custom processing method combination");
	}
	
	$output = <<END;
<h3>Show analysis Data:</h3>
<a href="$CGI_BASE_DIR/Microarray/bioconductor/upload.cgi?_tab=2&token=$jobname&show_norm_files=1">Show Files</a>
<h3>Output Files:</h3>
<a href="$RESULT_URL?action=view_file&analysis_folder=$jobname&analysis_file=${jobname}_annotated&file_ext=txt">${jobname}_annotated.txt</a><br>
<a href="$RESULT_URL?action=view_file&analysis_folder=$jobname&analysis_file=$jobname&file_ext=exprSet">$jobname.exprSet</a><br>
END
	
	$args = "";
	if ($cgi->param('process') eq "Custom") {
	    $args = ": " . join(' -> ', $cgi->param('custom'));
	}
	if ($cgi->param('process') eq "GCRMA") {
	    $args = "";  
	}
	
	
	$jobsummary = jobsummary('Files', join(', ', @filenames),
                             'Sample&nbsp;Names', join(', ', $cgi->param('sampleNames')),
                             'Processing', scalar($cgi->param('process')) . $args,
                             'Log 2 Transform', $cgi->param('log2trans')?"Yes":"No",	   
			#  'Copy&nbsp;back', $cgi->param('fmcopy') ? "Yes" : "No",
                             'E-Mail', scalar($cgi->param('email')));
	 my @db_jobsummary = ('File Names =>' . join(', ', @filenames),
			     'Log 2 Transform' .  $cgi->param('log2trans')?"Yes":"No",
			     'Sample Names =>' . join(', ', $cgi->param('sampleNames')),
			     'Processing =>'. $cgi->param('process')
			   );
	$script = generate_r($jobname, [@filenames]);
	
	$error = create_files($jobname, $script, $output, $jobsummary, 15, 
	                      "Affymetrix Expression Analysis", $cgi->param('email'));
	error($error) if $error;
    
    $job = new Batch;
    $job->type($BATCH_SYSTEM);
    $job->script("$RESULT_DIR/$jobname/$jobname.sh");
    $job->name($jobname);
    $job->out("$RESULT_DIR/$jobname/$jobname.out");
    $job->submit ||
    	error("Couldn't start job");
    open(ID, ">$RESULT_DIR/$jobname/id") || error("Couldn't write job id file");
    print ID $job->id;
    close(ID);
    log_job($jobname, "Affymetrix Expression Analysis", $fm);
##update the database with the analysis run info and add the user defined sample names to the XML file
    update_analysis_table(@db_jobsummary);
    my @all_samples = $cgi->param('sampleNames');
    update_xml_file(token		=>$jobname,
    				sample_names=>\@all_samples,
    				file_name   =>\@filenames, 
    			   );
 
    print $cgi->redirect("job.cgi?name=$jobname");
}

#### Subroutine: generate_r
# Generate an R script to process the data
####
sub generate_r {
	my ($jobname, $celfiles) = @_;
	my $celpath = $fm->path;
	my @sampleNames = $cgi->param('sampleNames');
	my $process = $cgi->param('process');
	my @custom = $cgi->param('custom');
	my $fmcopy = $cgi->param('fmcopy');
	my $script;
	
	my $slide_type_name = $affy_o->find_slide_type_name(file_names=>$celfiles);
	
	# Escape double quotes to prevent nasty hacking
	for (@$celfiles) { s/\"/\\\"/g }
	for (@sampleNames) { s/\"/\\\"/g }
	$process =~ s/\"/\\\"/g;
	for (@custom) { s/\"/\\\"/g }
	
	# Make R variables out of the perl variables
	$script = <<END;
filenames <- c("@{[join('", "', @$celfiles)]}")
filepath <- "$celpath"
samples <- c("@{[join('", "', @sampleNames)]}")
process <- "$process"
custom <- c("@{[join('", "', @custom)]}")
log2trans <- @{[$cgi->param('log2trans') ? "TRUE" : "FALSE"]}
lib_path <- "$R_LIBS"
chip.name <- "$slide_type_name"
path.to.annotation <- "$AFFY_ANNO_PATH/"

END

	# Main data processing, entirely R
	$script .= <<'END';
.libPaths(lib_path)
library(affy)
library(gcrma)
library(vsn)
bgcorrect.methods <- c(bgcorrect.methods, "gcrma")
normalize.AffyBatch.methods <- c(normalize.AffyBatch.methods, "vsn")
express.summary.stat.methods <- c(express.summary.stat.methods, "rlm")

#read in the annotation file
annot <- read.table(paste (path.to.annotation ,chip.name,"_annot.csv",sep=""),sep=",")
annot.orders <- order(annot[-1,1])
annot.header <- as.matrix(annot[1,])
annot.noheader <- annot[-1,]
annot.grab.columns <- c( grep("Representative Public ID",annot.header),grep("Gene Symbol",annot.header),grep("Gene Title",annot.header),grep("LocusLink",annot.header) )


setwd(filepath)
if (process == "RMA")
#    exprset <- rma(ReadAffy(filenames = filenames))
# This is causing an error on Linux but not Mac OS X
# More investigation needed
    exprset <- justRMA(filenames = filenames) #changed 10.21.04 Bruz
if (process == "GCRMA"){
	exprset <- justGCRMA(filenames = filenames)

}



if (process == "Custom") {
    affybatch <- ReadAffy(filenames = filenames)
    bgcorrect.param <- list()
    if (custom[1] == "gcrma-eb") {
        custom[1] <- "gcrma"
        gcgroup <- getGroupInfo(affybatch)
        bgcorrect.param <- list(gcgroup, estimate = "eb", rho = 0.8, step = 60, 
                                lower.bound = 1, triple.goal = TRUE)
    }
    if (custom[1] == "gcrma-mle") {
        custom[1] <- "gcrma"
        gcgroup <- getGroupInfo(affybatch)
        bgcorrect.param <- list(gcgroup, estimate = "mle", rho = 0.8, 
                                baseline = 0.25, triple.goal = TRUE)
    }
    exprset <- expresso(affybatch, bgcorrect.method = custom[1],
                        bgcorrect.param = bgcorrect.param,
                        normalize.method = custom[2],
                        pmcorrect.method = custom[3],
                        summary.method = custom[4])
}
colnames(exprset@exprs) <- samples
log2methods <- c("medianpolish", "mas", "rlm")
if (log2trans) {
    if (process == "Custom" && !(custom[4] %in% log2methods)) {
        exprset@exprs <- log2(exprset@exprs)
        exprset@se.exprs <- log2(exprset@se.exprs)
    }
} else {
    if (process == "RMA" || process == "Custom" && custom[4] %in% log2methods) {
        exprset@exprs <- 2^exprset@exprs
        exprset@se.exprs <- 2^exprset@se.exprs
    }
}
END

    # Output results
	$script .= <<END;
#Add in the annotaion information
Matrix <- exprs(exprset)
output <- cbind(Matrix)
output.orders <- order(row.names(Matrix))
output.annotated <- cbind(row.names(Matrix)[output.orders],annot.noheader[annot.orders,annot.grab.columns],output[output.orders,])
headings <- c("Probesets",annot.header[1,annot.grab.columns],sampleNames(exprset))
write.table(output.annotated,file="$RESULT_DIR/$jobname/${jobname}_annotated.txt" ,sep="\t",quote=FALSE,col.names = headings,row.names=FALSE)
#End writing out annotated table

save(exprset, file = "$RESULT_DIR/$jobname/$jobname.exprSet")
#Turn off writing just a plain non-annotated file
#write.table(exprs(exprset), "$RESULT_DIR/$jobname/$jobname.txt", quote = FALSE, 
#            sep = "\t", col.names = sampleNames(exprset))
END

	$script .= $fmcopy ? <<END : "";
save(exprset, file = "$celpath/$jobname.exprSet")
END

	return $script;
}

#### Subroutine: expresso_safe
# Check to see if the expresso call is valid and methods will work together
# Returns 1 if valid and 0 if not
####
sub expresso_safe {
	my ($bgcorrect, $normalize, $pmcorrect, $summary) = @_;

	if ($bgcorrect eq "rma" && $pmcorrect ne "pmonly") {
		return 0;
	}

	if (($summary eq "mas" || $summary eq "medianpolish") &&
		$pmcorrect eq "subtractmm") {
		return 0;
	}

	if ($normalize eq "vsn" && $bgcorrect ne "none") {
		return 0;
	}

	return 1;
}

#### Subroutine: error
# Print out an error message and exit
####
sub error {
    my ($error) = @_;

	print $cgi->header;    
	site_header("Affymetrix Expression Analysis: affy");
	
	print h1("Affymetrix Expression Analysis: affy"),
	      h2("Error:"),
	      p($error);
	
	print "DEBUG INFO<br>";
	my @param_names = $cgi->param;
	foreach my $p (@param_names){
		print $p, " => ", $cgi->param($p),br; 
	}
	site_footer();
	
	exit(1);
}


#### Subroutine: Update Analysis record
# Once an analysis run has start update the db record with the switches that were used
# Give a hash from the cgi->parms;
# Return 1 for succesful update 0 for a failure
####
sub update_analysis_table {
	my @db_jobsummary = @_;
	my $analysis_data = join ('// ', @db_jobsummary);
#	my %cgi_params = @_;
	my $analysis_id = $cgi->param('analysis_id');
#	my @R_switches = qw(process custom log2trans path sampleNames);
#	my $analysis_data = '';
	
	error("Analysis ID not FOUND '$analysis_id'") unless ($analysis_id =~ /^\d/);
	
#	foreach my $key (@R_switches){
#		if (exists $cgi_params{$key}){
#			my $val = $cgi_params{$key} ? $cgi_params{$key} : "Not Set";
#			$analysis_data .=  "$key=>$val //";
#		}
#	}
#	$analysis_data =~ s/[^a-zA-Z0-9\/_\.=>  ]/__/g;	#remove any junk from the analsysis annotation note
#	$log->debug("ANALYSIS ANNO '$analysis_data'");
	my $rowdata_ref = { 	analysis_description  => $analysis_data,	
						        
					  };
					  
	 
	 my $result = $sbeams->updateOrInsertRow(
	 		update=>1,
            table_name=>$TBMA_AFFY_ANALYSIS,
            rowdata_ref=>$rowdata_ref,
            PK=>'affy_analysis_id',
            PK_value=>$analysis_id,
            return_PK=>1,
            verbose=>0,
            testonly=>0,
            add_audit_parameters=>1,
            );
}

#### Subroutine: update_xml_file
# Once an analysis run has started update the xml sample group file with the sample names used
# return 1 for success 0 for failure
####
sub update_xml_file {
	
	my %args = @_;
	my $folder_name = $args{token};
    my $all_sample_names_aref = $args{sample_names};
    my @all_filenames = @{ $args{file_name} };
    
    my $xml_file = "$BC_UPLOAD_DIR/$folder_name/$SAMPLE_GROUP_XML";
    my $parser = XML::LibXML->new();
	my $doc = $parser->parse_file( $xml_file);	
    my $root  = $doc->getDocumentElement;
    
    my %class_numbers = ();
	my $class_count = 0;
  ##need to convert the sample name to a number since R only wants two classes for t-testing O and 1
  ##First frind the reference sample node to use as the class 0	
		
		#$sample_groups{SAMPLE_NAMES}{$sample_name} = "$class";  
  
   my $reference_sample_group_node = $root->findnodes('//reference_sample_group');
   
   my $reference_sample_group = $reference_sample_group_node->to_literal;
  if ($reference_sample_group){
  	$class_numbers{$reference_sample_group} = $class_count;
  	$class_count ++;
  }else{
  	error("Cannot find the reference sample group node");
  }
  
  
    for(my $i=0; $i <= $#all_filenames; $i++){
    	my $file_name = $all_filenames[$i];
    	my $sample_name = $all_sample_names_aref->[$i];
    	my $found_flag = 'F';
    	my $x_path = "//file_name[.='$file_name']";
   # print STDERR "FILE NAME '$file_name'";
	    my $count = 0;
	    foreach my $c ($root->findnodes($x_path)) {
			$found_flag = 'T';
			my $sample_group = $c->findnodes('./@sample_group_name')->string_value();
			$c->setAttribute("sample_name", $sample_name);
		    
		    my $node_val = $c->to_literal;
		    
		   
### Need to add a class number that will be used by R in the t-test and anova test.  It cannot use
### a sample_group name for determing the different classes....
		    my $class = '';
		    
		    if (exists $class_numbers{$sample_group}){		
				$class = $class_numbers{$sample_group};
			}else{
				$class_numbers{$sample_group} = $class_count;
				$class = $class_numbers{$sample_group};
				$class_count ++;
			}
	    	$c->setAttribute("class_number", $class);
	    	 
	 
	    	 
	    	 print STDERR "NODE VAL '$sample_group' CLASS '$class'\n";
	   
	    	if ($count > 1){
	    		error("Updating XML Error: More then two files with the same name $file_name");
	    	}
	    	$count ++;
	    }
    	  print STDERR "COULD NOT FIND NODE FOR FILE '$file_name'" unless $found_flag eq 'T';
	}
	
	
	my $state = $doc->toFile($xml_file, 1);	#1 is the xml format to produce, it will make a nice looking indented pattern
     
}
    				
    				
    				
