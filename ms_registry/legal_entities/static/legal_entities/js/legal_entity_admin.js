(function ($) {
    'use strict';

    function toggleEntityFields() {
        var entityType = $('#id_entity_type').val();

        // Django admin puts fieldset classes on inner divs, not the fieldset itself
        // Target the parent fieldset of these classed elements
        var legalPersonFieldset = $('.legal-person-fieldset').closest('fieldset');
        var naturalPersonFieldset = $('.natural-person-fieldset').closest('fieldset');

        // Debug logging
        console.log('Entity type value:', entityType);
        console.log('Legal person fieldset found:', legalPersonFieldset.length);
        console.log('Natural person fieldset found:', naturalPersonFieldset.length);

        if (entityType === 'legal_person') {
            legalPersonFieldset.show();
            naturalPersonFieldset.hide();
        } else if (entityType === 'natural_person') {
            legalPersonFieldset.hide();
            naturalPersonFieldset.show();
        } else {
            // Show both if no selection
            legalPersonFieldset.show();
            naturalPersonFieldset.show();
        }
    }

    $(document).ready(function () {
        console.log('Legal entity admin JS loaded');

        // Initial toggle on page load
        toggleEntityFields();

        // Toggle on entity_type change
        $('#id_entity_type').on('change', function () {
            console.log('Entity type changed');
            toggleEntityFields();
        });
    });
})(django.jQuery);
