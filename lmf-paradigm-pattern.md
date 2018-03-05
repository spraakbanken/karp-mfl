# JSON-structure for the LMF Morphological Patterns package

The following should emulate a parsed pfile into LMF and further
transformed and condensed into JSON.

The reason why this is so verbose is because it is intended to specify the
building of many kinds of morphological technology.

The data (should) reflects this:

`1+e::msd=sg indef nom#1+es::msd=sg indef gen	0=sopsäckshållare..nn.1,,1=sopsäckshållar#0=solvärmefångare..nn.1,,1=solvärmefångar#0=socialmedicinare..nn.1,,1=socialmedicinar`

```javascript
{
  "MorphologicalPatternID": "id-string", // or a list of IDs?
  "VariableInstances": [ // this information could be moved under 'Affix'-information in LMF standard, but that seems too far fetched
    {0: "sopsäckshållare..nn.1", 1: "sopsäckshållar"}, // use 'id' instead of 0?
    {0: "solvärmefångare..nn.1" ,1: "solvärmefångar"},
    {0: "socialmedicinare..nn.1", 1: "socialmedicinar"}
  ],
  "TransformSet": [
    {"Process": [
       {
	 "operator": "addAfter", // this should be standard 'addAfter' for concatenating
	 "processType": "pextractAddVariable", // this is pextract specific, rename?
	 "variableNum": "1" // could be 'stringValue', but now matches use of integers in VariableInstances
       },
       {
	 "operator": "addAfter",
	 "processType": "pextractAddConstant",
	 "stringValue": "e"
       }
     ],
     "GrammaticalFeatures": [
       {"msd": "sg indef nom"}
     ],
     "TransformCategory": {},
     "feat": [{}] // just in case?
    },
    {
      "Process": [
	{
	  "operator": "addAfter",
	  "processType": "pextractAddVariable",
	  "variableNum": "1"
	},
	{
	  "operator": "addAfter",
	  "processType": "pextractAddConstant",
	  "variableNum": "es"
	}
      ],
      "GrammaticalFeatures": [
	{"msd": "sg indef gen"}
      ]
    }
  ]
}
```