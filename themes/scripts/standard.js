function element_has_class(element, class_name){
	var r = new RegExp('\\b' + class_name + '\\b');
	return r.test(element.className);
}

// make a child fill it's parent clientHeight - we may still need to adjust this for margins/padding
function stretch_heights(){
	var elements = document.getElementsByTagName("*");
	// set all stretchables back to auto height
	for (var i=0; i < elements.length; i++) {
	    if(element_has_class(elements[i], 'stretch_height')){
	    	elements[i].style.height = 'auto';
	    }
	}	
	// stretch height
	var s = '';
	for (var i=0; i < elements.length; i++) {
	    if(element_has_class(elements[i], 'stretch_height')){
	    	elements[i].style.height = elements[i].parentNode.clientHeight+'px';
	    }
	}
}
