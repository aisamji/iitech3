# iitech3
A command line program to automate much of the repetitive work when templating the Ismaili Insight newsletter. The program is called by using one of its subcommands:
- `repair` fixes any errors with the HTML template that are preventing it from loading properly.
- `review` scans and fixes, if possible, all the links in the HTML template and verifies their utility and correctness.
- `apply` reads a YAML transformation file and applies the transformations described therein to the HTML template.
- `lookup` gets the status of an email address or a url from the cache or from an online lookup.
- `mark` sets the status of an email address or a url in the cache.

For help on any command, `iitech3 help` can be called.

# options
Other than the commands, there are a couple of options that can be used without calling any commands. `iitech3 help` prints out the help text. `iitech3 version` prints out the version information.

# repair
The `repair` command scans the HTML template it is given and fixes many common mistakes. Currently the list of mistakes that can be fixed is:
- Add the missing 'i' in 'ismailinsight.org' to make 'ismailiinsight.org'.
- Remove all useless `<style>` tags in the `<head>`. These are usually added by browser extensions like Grammarly.  
  *NB: While techniques like the ones Grammarly is using would work on a regular HTML page, using them on an online HTML template like the one in eNewsletterPro results in 10,000+ lines of useless code that slows down the website and would most likely prevent the newsletter from being received due to size restrictions on many email servers.*
- Add the gray background if it is missing.

Usage:
```
iitech3 repair -p
iitech3 repair template.html
```

# review
The `review` command scans the HTML template to check the validity of links. It corrects any links that it can and marks the ones that it can't. The review operation verifies and validates email links, jump links, and absolute links.
Usage:
```bash
iitech3 review -p
iitech3 review template.html
```

## Email Links
- Invisible links (i.e. links that do not have any display text) are removed.
- Spaces in email addresses are removed since these are likely a mistake and cause result in an invalid email address when composing the message.
- The email address is marked as \*INVALID* if the email address doesn't exist. (e.g. This is an invalid email: [\*INVALID rejected_email*Richard](mailto:richard@quickemailverification.com))
- The email address is marked as \*UNCHECKED* if the email server prevents scripts like this from validating their email addresses. For these email addresses, an [external service](http://verify-email.org/) that is allowed to the validate the email address could be used. (e.g. This email could not be checked: [\*UNCHECKED*newsletters@IsmailiInsight.org](mailto:newsletters@IsmailiInsight.org))

## Jump Links
- Invisible links (i.e. links that do not have any display text) are removed.
- Marked as \*MISSING* if the referenced anchor is missing (e.g. [\*MISSING ReturnTop*Return to Top](#ReturnTop))

## Absolute Links
- Invisible links (i.e. links that do not have any display text) are removed.
- Blank links (i.e. links that do not have a destination) are removed. (e.g. This goes to [nowhere]().)
- All links are set to open in a new window.
- Tracked links are decoded since the eNewsletterPro will add the tracker for the current newsletter upon sending. These types of links usually result when a link is copied from an already sent version of the template, whether it be from someones email or from eNewsletterPro. (e.g [Journey For Health](http://www.ismailiinsight.org/enewsletterpro/t.aspx?url=https%3A%2F%2Fjourneyforhealth.org) becomes [Journey For Health](https://journeyforhealth.org))
- Links are marked as \*BROKEN* if they could not be reached. (e.g. [\*BROKEN 500*www.journeyforhealth.org](https://www.journeyforhealth.org))
- Links are marked as \*UNCHECKED* if the website does not allow scripts to query their website. (e.g. [\*UNCHECKED*AKF USA](http://www.akfusa.org/about-us/))

# apply
The `apply` command reads in a transformation file and applies the specified transformations to the HTML template. The transformation file is written in YAML and only supports transforming the top picture (i.e. National) and the articles.
In the file, the target for a transformation is identified by the article title. The transformation consists of one or more specifiers (i.e. title, prepend, append, replace, left, right) and a one or more content descriptors.
Usage:
```bash
iitech3 apply national.json -p
iitech3 apply regional.json template.html
```
*NB: The title used for identification is the one from before the transformation is applied*

## Transformation File
The transformation file contains a set of transformations to be applied to an HTML template. These transformations can change the top (i.e. National) picture and/or any of the articles. The transformations are described by an identifier, a specifiers, and one or more content descriptors. An example of all the identifiers, specifiers, and content descriptors can be found in [transform_sample.yml](transform_sample.yml).

### Content Descriptors
Content descriptors form are the most important aspects of transformation files. Content descriptors come in 2 main flavors. They can be a text literal . . .
```yaml
Quotes are not necessary for a text literal.
```
```yaml
' Unless if you want to keep leading and/or trailing spaces '
```
Or they can be a group of one or more attributes . . .
```yaml
link: https://www.google.com
text: Custom display text for the link is not necessary.
```
There are many content descriptors and by combining them properly, it is possible to transform the HTML template however you desire. Most anywhere a content descriptor can be used. A list of content descriptors can also be used. This allows one to sequence multiple content descriptors to more accurately describe the end result.
```yaml
- Any text that is going to be displayed can
- ' be described with a '
- bold: content descriptor
- ' or a '
- bold: list of content descriptors
- .
```

### Identifiers
Identifiers, true to their name, are used to identify the target of the transform. Other than the special `top` identifier, targets are identified by the article title.
*NB: The article title that is used for identification is the title of the article before it is transformed.*

### Specifiers
Specifiers further narrow down the target to either transforming the `title` or transforming the body (`prepend`, `append`, `replace`, `left`, `right`).
Of the 5 body specifiers, `left` and `right` are mutually exclusive from the other 3 and these 2 must appear together. If any of the other 3 are present, they will be ignored. In addition, the `replace` specifier takes precedence over the `append` and `prepend` specifiers, so the body will be replaced before anything is appended or prepended to it.

# lookup
The `lookup` command is used to lookup the status of an email address or webpage. By default, the lookup command looks for the requested value in the cache and if it is not found or if it is out-of-date (age >= 2 weeks) then, and only then, the status is retrieved from online and an entry is added to the cache.
With the `--cached` option, the status will not be retrieved from online for any reason, failing when the entry is not in the cache. The `--forced` option on the other hand, will force the status to be retrieved from online before the cache is checked. These 2 options are optional and mutually exclusive.
Usage:
```bash
iitech3 lookup email --cached ali.samji@outlook.com
iitech3 lookup webpage --forced https://www.google.com
```

# mark
The `mark` command is used to edit mark the status of a webpage or email address in the cache. This is useful for those email addresses and webpages that cannot be checked by scripts. Depending on the type you specify (email or webpage), the arguments to specify the status are different.
Usage:
```bash
iitech3 mark email --valid lcc@usaji.com
iitech3 mark webpage --ok http://www.akfusa.com
```
