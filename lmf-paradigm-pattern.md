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
  "VariableInstances": [
    {"first-attest": "sopsäckshållare..nn.1", "1": "sopsäckshållar"},
    {"first-attest": "solvärmefångare..nn.1" ,"1": "solvärmefångar"},
    {"first-attest": "socialmedicinare..nn.1", "1": "socialmedicinar"}
  ],
  "TransformCategory": [ // paradigm specific categories
    {"name": "fm_paradigm", "classes": ["p_apa", "p_bepa"]},
    {"name": "deklination", "classes": ["1", "8"]}
  ],
  "TransformSet": [
    {"Process": [
       {
	 "operator": "addAfter", // this should be standard 'addAfter' for concatenating
	 "processType": "pextractAddVariable", // this is pextract specific, but need not be prefixed with 'pextract', rename?
	 "variableNum": "1" 
       },
       {
	 "operator": "addAfter",
	 "processType": "pextractAddConstant",
	 "stringValue": "e"
       }
     ],
     "GrammaticalFeatures": {
         "msd": "sg indef nom"
       },
     "TransformCategory": [{}], // wordform specific categories
     "feat": [{}] // placeholder just in case
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
	  "stringValue": "es"
	}
      ],
      "GrammaticalFeatures":
	{
	  "msd": "sg indef gen"
	},
      "TransformCategory": [{}],
      "feat": [{}]
    }
  ]
}
```