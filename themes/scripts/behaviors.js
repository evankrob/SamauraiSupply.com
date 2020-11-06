if (typeof $ == "undefined") alert("jQuery core is required for this theme.");

/**
 * Namespace for nav-related functions.
 */
var nav = {
	
	accordion: {
		
		/**
		 * Initializes accordion menus.
		 */
		initialize: function() {
			var $accordion = $(".nav_accordion");
			$accordion.removeClass("nav_menu");
			$accordion.find("li").has("ul").addClass("has_children");
			$accordion.find("li").click(nav.accordion.onClick);
		},
		
		/**
		 * Preselects the accordion section that best matches the current page, if any.
		 */
		preselect: function() {
			$(".nav_accordion").each(function() {
				var matches = $(this).find("a").filter(function() {
					var href = $(this).attr("href").replace(/[#\/]*/gi, "");
					return (href == document.location.pathname.replace(/[#\/]*/gi, ""));
				});

				matches.eq(0).parentsUntil(".nav_accordion").filter(".has_children").addClass("expanded").children("ul").css("display", "block");
			});
		},
		
		/**
		 * Event handler for when an item in an accordion menu is clicked.
		 */
		onClick: function(e) {
			e.stopPropagation();
			var $this = $(this);
			if ($this.hasClass("has_children")) {
				e.preventDefault();
				$this.siblings().removeClass("expanded").children("ul").slideUp(400);
				if ($this.hasClass("expanded"))
					$this.removeClass("expanded").children("ul").slideUp(400);
				else
					$this.addClass("expanded").children("ul").slideDown(400);
			}
		}
		
	},
	
	tiered: {
		
		/**
		 * Initializes 2-Tiered menus.
		 */
		initialize: function() {
			$(".nav_tier").each(function() {
				var $nav_tier = $(this);
				var topHtml = "";
				var bottomHtml = "";
				$nav_tier.children("li").each(function() {
					topHtml += "<li>" + $(this).children("a").clone().wrap('<div>').parent().html() + "</li>";
					if ($(this).has("ul").length > 0)
						bottomHtml += $(this).children("ul").clone().wrap('<div>').parent().html();
					else
						bottomHtml += "<ul></ul>";
				});
				
				$nav_tier.after($(bottomHtml).addClass("nav_tier_bottom").addClass("nav_menu").hide());
				$nav_tier.after("<ul class='nav_tier_top'>" + topHtml + "</ul>");
				$nav_tier.hide();
			});
			$(".nav_tier_top li").click(nav.tiered.onClick);
		},
		
		/**
		 * Preselects the top-tiered menu item that best matches the current page, if any.
		 */
		preselect: function() {
			$(".nav_tier_top").each(function() {
				var match = $(this).find("a").filter(function() {
					var href = $(this).attr("href").replace(/[#\/]*/gi, "");
					return (href == document.location.pathname.replace(/[#\/]*/gi, ""));
				});
				if (match.length > 0) {
					var selectedOption = match.first().parent();
					selectedOption.addClass("selected");
					var selectedIndex = selectedOption.parent().children().index(selectedOption);
					$(this).siblings(".nav_tier_bottom").hide();
					var candidate = $(this).siblings(".nav_tier_bottom:eq(" + selectedIndex.toString() + ")");
					if (candidate.find("a").length > 0) {
						candidate.show();
					}
				} else {
					var match = $(this).siblings(".nav_tier_bottom").find("a").filter(function() {
						var href = $(this).attr("href").replace(/[#\/]*/gi, "");
						return (href == document.location.pathname.replace(/[#\/]*/gi, ""));
					});
					
					if (match.length > 0) {
						var selectedOptions = match.first().parentsUntil(".nav_tier_bottom").parent();
						var selectedIndex = selectedOptions.parent().children(".nav_tier_bottom").index(selectedOptions);
						$(this).children("li:eq(" + selectedIndex + ")").click();
					} else {
						match = $(this).find("a").filter(function() {
							var href = $(this).attr("href").replace(/[#\/]*/gi, "");
							return (href == document.location.pathname.replace(/[#\/]*/gi, ""));
						});
						if (match.length > 0)
							match.first().parent().addClass("selected");
					}
				}
			});
		},
		
		/**
		 * Event handler for when a header item in the 2-Tier menu is clicked.
		 */
		onClick: function(e) {
			e.stopPropagation();
			$this = $(this);
			$parent = $this.parent();
			$this.addClass("selected").siblings("li").removeClass("selected");
			$parent.siblings(".nav_tier_bottom").hide();

			var index = $parent.find("li").index($this);
			$match = $parent.siblings(".nav_tier_bottom:eq(" + index + ")"); 
			if ($match.length > 0) {
				var $thisHref = $this.find("a").attr("href");
				if ($thisHref == null || $thisHref == "") {
					e.preventDefault();
				}
				if ($match.find("a").length > 0) {
					$match.show();
				}
			}
		}
		
	}
	
};

$(function() {
	nav.accordion.initialize();
	nav.tiered.initialize();
	nav.accordion.preselect();
	nav.tiered.preselect();
});
