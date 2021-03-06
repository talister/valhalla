## 1.3.11
2017-10-09

* Added completion_threshold to compose UI and set default value to 90.0%

## 1.3.10
2017-10-06

* Fix vis.js Timeline tooltips

## 1.3.9
2017-10-05

* Unify pond block statuses and colors with the scheduler visualization

## 1.3.8
2017-10-04

* Compact typography for proposal submissions

## 1.3.7
2017-09-29

* Auto redirect to first request detail if userrequest only contains a single request
* Preserve linebreaks from textfields in proposal submission
* Link to correct getting started guide
* Add legend to visibility plot history on request detail page

## 1.3.6
2017-09-26

* Add NRES to pressure and contention plots

## 1.3.5
2017-09-26

* Add media/ to dockerignore

## 1.3.4
2017-09-22

* Restrict username length on profile update page to 50 characters
* Filter comissionig instruments from available instruments on compose page

## 1.3.3
2017-09-21

* Add softies to ADMINS
* Add support for NRES to user interface

## 1.3.2
2017-09-19

* Fix NRES overheads

## 1.3.1
2017-09-18

* Add API quota to profile API
* Restrict lengths of username, target name to 50 characters

## 1.3
2017-09-12

* Various typo fixes
* Prevent large cadences from overflowing the screen and forcing user to refresh the page
* Uprev python & JS deps
* Properly format fail reason in external BlockSerialize
* Update docker base image to stretch
* Show api quota on profile page
* Use cdn.lco.global for all assets

## 1.2.3
2017-08-25

* Add completion_threshold model field to request.
* Modify update request state with pond blocks code to calculate completion_percent and compare to threshold.

## 1.2.2
2017-08-15

* Add custom 404 page so users being redirected from the scheduler visualization don't get confused.

## 1.2.1
2017-08-07

* Add legend to block history plot
* Fix bug in request serializer that would attempt to order by method attributes

## 1.2
2017-08-04

* Pin rise set
* Revise throttle limits

## 1.1.12
2017-07-27

* Fix problem with setuptools and travis ci
* Dont perform LookUP is target is not Sidereal
* Fix compatibility with latest responses library
* Set max airmass to 2 for simple interface users
* Allow unicode in compose page
* Fix paramter for active proposals in manage proposals link

## 1.1.11
2017-07-24

* Add separate health check endpoint

## 1.1.10
2017-07-24

* Add request logging at a more granular level
* Fix bug in lookUP so only last call is used

## 1.1.9
2017-07-18

* Uprev some dependencies

## 1.1.8
2017-07-18

* Use rp filter for "red"

## 1.1.7
2017-07-17

 * Don't use html in plain text emails
 * Remove use of mutable querydict
 * Add additional users to admin list

## 1.1.6
2017-07-06

* Return target name for satellite targets
* Make molecule priority a read only field
* Allow valhalladev host
* Catch correct ConnectionError
* Validate that molecule type matches instrument

## 1.1.5
2017-06-22

* Submitted a request will automatically set the priority of molecules in ascending order

## 1.1.4
2017-06-20

* Enable color/high res images for proprietary data

## 1.1.3
2017-06-20

* Install libcairo2 from debian stretch as the version in jessie is too old for WeasyPrint

## 1.1.2
2017-06-20

* Increase AccessToken expire time
* Add periodic task to remove expired tokens every 24hrs
* Send notification email when DDT proposal is submitted
* Fix some typos and other erorrs in sciapplication detail template

## 1.1.1
2017-06-19
* Removed any timeout from the cached isDirty_query_time

## 1.1
2017-06-19

* Add default IPP values on timallocation creation
* Make data jpg preview link to larger jpg version of frame
* Add link to color version of jpg for a frame if available
* Show instrument name instead of code in request detail
* Remove public field from semester
* Fix vis.js version as newest version breaks legend

## 1.0.8
2017-06-15

* Return empty block set when pond is unreachable instead of thowing exception
* Inform user when data is in transit when request is in completed state

## 1.0.7
2017-06-13

* Make UWSGI logs match LCO internal logging format
* Fix bug where adding calibration frames did not update request duration
* Add LogEntry admin so we can keep track of who changes what in the admin
* Validate that windows fit within a defined semester

## 1.0.6
2017-06-08

* Fix ADMINS setting to send emails on server errors
* Fix bug where adding a user to a proposal that was already a member caused a crash
* Change profile endpoint to return all proposals for a user
* Upgrade numpy to 1.13
* Fix a bug in downloading data from userrequests that have many requests

## 1.0.5
2017-06-07

* Add socket-timeout uwsgi option in hopes of avoding corrupt reponse to scheduler enpoint

## 1.0.4
2017-06-06

* Show dates in UT on request detail page
* Change logo to link to lco.global
* Add warning if user is throttled when trying to cancel request
* Prefetch related models in userrequest viewset
* add exclude state filter to userequests

## 1.0.3
2017-06-06

* Increased throttle limits
* Made state read only in Request Serializer

## 1.0.2
2017-06-05

* Added processes to uwsgi
* Fix a bug with zero padding and the pond

## 1.0.1
2017-06-05

* Added two additional filters to userrequests for fitlering on sub requests last update time

## 1.0.0
2017-06-02

* Added button to download API view json on compose page.
* Enable pagination of child requests.
* Fix various inconsistencies between documentation and code.
* Improve UserRequest admin pages.
* Hardcode out NRES.
* Provide simple filter names for ed users.
* Fixed bug with old version of firefox on compose page.
* Refactored telescope states endpoint.
* isDirty fixes.

## 0.7.1
2017-05-22

* Add NRES fields

## 0.7.0
2017-05-19

* Show instrument name instead of fail count on request details
* Remove Valhalla from page titles
* Allow input of RA/Dec with spaces instead of colons
* Minor bug fixes on compose page
* Locked dependencies
* Add API throttling
* Cache rise/set calculations on a per request basis
* Accurate Pressure plot. Backend and UI updates. Now with site lines!
* Fixes for scheduler interface
* Enable failed count
* Add confirmation before submitting observation on compose page
* Misc bug fixes for rise/set calculations
* Exposure time no longer defaults to 30 seconds. It is now blank.
* Added extra context to pressure and contention endpoints
* Misc text updates.

## 0.6.0
2017-05-11

* Fix bugs with cadence UI not using UTC.
* Fix bug that was caused by target names being strictly numerical.
* Add confirmation dialog to panels on the compose page before removal.
* Text updates and corrections.
* Added Google Analytics and improved logging
* Improvements to admin proposal view (/proposals/semester/2017AB) etc.
* Improve/fix some unit tests
* Add an ordering filter to the homepage. Ability to order by title, created time, updated time, last window.
* Added a target name filter to the front page.
* Minor CSS improvements for a more consistent appearance.

## 0.5.0
2017-05-05

* Fix milliseconds to 0 for telescope availability
* Fix wrong parameter name in telescope availability
* capitalize Observing Budget Explanation
* capitalize Observing Budget Explanation
* Added more specific language about what proposals should and should not be submitted through the portal
* Change help text for proper motions
* fix typo
* changes to defocus, guiding help text
* change Airmass help text
* Modify acquire mode/radius help text

## 0.4.2
2017-05-01

* Fix for removal of default floyds slit

## 0.4.1
2017-05-01

* Reformat Help page
* Make group id appear as Title in error messages
* Fix bug preventing call to action from showing up on homepage


## 0.4.0
2017-04-28

* Use more consistent validation messages for fields that are required
* Rename help on compose page to How to use this page
* Fix pdf rendering for non firefox browsers
* Remove moon phase from ddt proposal views
* Don't ask user to submit a proposal if they actually do have proposals
* Make sure users can always view their data when viewing a request in the archive by setting the start date to 2014
* Make planning tools link to planning tools on lco.global
* Correct behaviour of minor planet vs comet target composition. Make sure that 0 values in target helper do no validate as false
* Remove STANDARD from molecules that should be counted for acquire duration. Add acquire duration for every spectrum in the request
* Indicate simple interface by header logo
* hide proposal members from education users
* In compose form, use proposal titles instead of ids
* Hide even more stuff in simple interface
* Notify existing users when they have been added to a proposal
* Add better error messages when a request does not fit in any visible windows
* Made telescope availability chart more readable
* Description of epoch of elements
* Misc typo fixes
* Expanded help text; added internal/external links

## 0.3.0
2017-04-21

* Remove Submit Proposal link from Nav bar, and make it a link on the Manage Proposals page.
* Added additional help text to notifications_enabled on profile form
* Add link to terms of service
* Address user by first/last name in activation email
* Add link to login form from account activated page
* Change order and display of proposals in userrequest list filter
* close datetime picker on userrequest filter when date is chosen
* Show form errors in sidenav on compose page
* open links on compose page in new tabs, improve filter required error message
* remove instruments from ddt proposal
* remove link to rapid response documentation
* remove deadlines from ddt proposals
* Format field names in sidenav
* Add 1meter nres to spectrographs in configdb is_spectrograp
* Show message when target lookup fails on compose page, improve wording for archive lookup
* hide binning and defocus on spectra observations, default guiding to on for spectra observations
* default exposure time to 60 seconds for calibration molecules on compose page
* Add missing epochofel field for non sidereal target
* Increase alert timeout to 10 seconds
* Allow dec input to accept seconds gt 59 and less than 60
* Only show observation type if it is rapid response
* Change Child Requests to Sub-requests
* Add tooltip to duration on userrequest row
* Add additional wording to automatic calibration generation
* Simple interface
* add new profile settings and forms
* Implement on authored only email notifications
* Remove binning from compose page
* set max value validation on proper_motion_ra/dec, epoch and parallax
* Webkit does not support const. Fix strange caret css problem with webkit.
* Use friendly instrument names in compose form
* Add link to Rapid Response webpage
* Add link to ETC in new tab
* Fix configuration typo
* All caps IPP
* Add text for RR mode
* Add link to airmass limit webpage
* Add to desc of airmass
* Modify Observing Budget text
* Mods to Obs budget explanation, DDT justification
* Help for defocus, guiding
* Modified slit position, angle
* Modify acquire mode
* Expanded Call for Proposals section
* Modified Your Proposals text
* LCO staff and IAC eligible for standard proposals
* Moon Phase
* Change moon selection from Either to Any
* IPP = INtraProposal Priority

## 0.2.0
2017-04-14

* Format fields in request detail page
* Upgrade to django 1.11
* Format floats in request detail properly
* Prevent fields on compose page from losing focus when validation occurs
* Various typos fixed
* Switch contention plot to chart.js
* Header navigation CSS changes
* Make tools link actually point to the tools page
* Make admin page for requests and user requests load much faster
* Add 'duration' field to API output for getting requests
* Add 'location' details to API output for requests only if they are not blank (I.e. site, observatory, telescope info)
* Add semester_contains filter to /api/semesters endpoint to get semester details given a date[time]
* Initial working pressure and contention plots

## 0.1.0
2017-04-07

* Initial internal release
