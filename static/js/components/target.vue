<template>
  <panel :id="'target' + $parent.$parent.index" :errors="errors" v-on:show="show = $event"
         :canremove="false" :cancopy="false" icon="fa-crosshairs" title="Target" :show="show">
    <div class="alert alert-danger" v-show="errors.non_field_errors" role="alert">
      <span v-for="error in errors.non_field_errors">{{ error }}</span>
    </div>
    <div class="row">
      <div class="col-md-6 compose-help" v-show="show">
        <archive v-if="target.ra && target.dec" :ra="target.ra" :dec="target.dec"></archive>
      </div>
      <div :class="show ? 'col-md-6' : 'col-md-12'">
        <form class="form-horizontal">
          <customfield v-model="target.name" label="Target Name" field="name" v-on:input="update" :errors="errors.name">
          </customfield>
          <div class="row" v-show="lookingUP || lookupFail">
              <span class="col-md-12" style="text-align: right">
                <i v-show="lookingUP" class="fa fa-spinner fa-spin fa-fw"></i> {{ lookupText }}
              </span>
          </div>
          <customselect v-model="target.type" label="Type" field="type" v-on:input="update" v-if="!simple_interface"
                        :errors="errors.type" desc="Please select whether this is a sidereal or non-sidereal target."
                        :options="[{value: 'SIDEREAL',text: 'Sidereal'}, {value: 'NON_SIDEREAL',text:'Non-Sidereal'}]">
          </customselect>
          <div class="sidereal" v-show="target.type === 'SIDEREAL'">
            <customfield v-model="target.ra" label="Right Ascension" type="sex" field="ra" v-on:blur="updateRA" :errors="errors.ra"
                         desc="Decimal degrees or HH:MM:SS.S">
            </customfield>
            <customfield v-model="target.dec" label="Declination" type="sex" field="dec" v-on:blur="updateDec" :errors="errors.dec"
                         desc="Decimal degrees of DD:MM:SS.S">
            </customfield>
            <customfield v-model="target.proper_motion_ra" label="Proper Motion: RA" field="proper_motion_ra"
                         v-on:input="update" :errors="errors.proper_motion_ra" desc="Units are milliarcseconds per year. Max 20000."
			                   v-if="!simple_interface">
            </customfield>
            <customfield v-model="target.proper_motion_dec" label="Proper Motion: Dec" field="proper_motion_dec"
                         v-on:input="update" :errors="errors.proper_motion_dec" desc="Units are milliarcseconds per year. Max 20000."
			                   v-if="!simple_interface">
            </customfield>
            <customfield v-model="target.epoch" label="Epoch" field="epoch" v-on:input="update" :errors="errors.epoch"
                         desc="Julian Years. Max 2100." v-if="!simple_interface">
            </customfield>
            <customfield v-model="target.parallax" label="Parallax" field="parallax" v-on:input="update"
                         :errors="errors.parallax" desc="+0.45 mas. Max 2000." v-if="!simple_interface">
            </customfield>
          </div>
          <div class="non-sidereal" v-show="target.type === 'NON_SIDEREAL'">
            <customselect v-model="target.scheme" label="Scheme" field="scheme" v-on:input="update" :errors="errors.scheme"
                          :options="[{value: 'MPC_MINOR_PLANET', text: 'MPC Minor Planet'}, {value: 'MPC_COMET', text: 'MPC Comet'}]"
                          desc="The orbital elements scheme to use with this target.">
            </customselect>
            <customfield v-model="target.epochofel" label="Epoch of Elements" field="epochofel"
                         v-on:input="update" :errors="errors.epochofel" desc="The epoch of the orbital elements in MJD.">
            </customfield>
            <customfield v-model="target.orbinc" label="Orbital Inclination" field="orbinc" v-on:input="update"
                        :errors="errors.orbinc">
            </customfield>
            <customfield v-model="target.longascnode" label="Longitude of Ascending Node" field="longascnode"
                          v-on:input="update" :errors="errors.longascnode" desc="Angle in Degrees">
            </customfield>
            <customfield v-model="target.argofperih" label="Argument of Perihelion" field="argofperih"
                          v-on:input="update" :errors="errors.argofperih" desc="Angle in Degrees">
            </customfield>
            <customfield v-model="target.eccentricity" label="Eccentricity" field="eccentricity"
                          v-on:input="update" :errors="errors.eccentricity" desc="0 to 0.99">
            </customfield>
          </div>
          <div class="minor-planet" v-show="target.scheme === 'MPC_MINOR_PLANET'">
            <customfield v-model="target.meandist" label="Mean Distance (AU)" field="meandist"
                         v-on:input="update" :errors="errors.meandist" desc="Astronomical Units">
            </customfield>
            <customfield v-model="target.meananom" label="Mean Anomoly" field="meananom"
                         v-on:input="update" :errors="errors.meananom" desc="Angle in Degrees">
            </customfield>
          </div>
          <div class="mpc-comet" v-show="target.scheme === 'MPC_COMET'">
            <customfield v-model="target.perihdist" label="Perihelion Distance" field="perihdist"
                         v-on:input="update" :errors="errors.perihdist" desc="in AU">
            </customfield>
            <customfield v-model="target.epochofperih" label="Epoch of Perihelion" field="epochofperih"
                         v-on:input="update" :errors="errors.epochofperih" desc="Modified Juian Days">
            </customfield>
          </div>
          <div class="spectra" v-if="showSlitPosition">
            <customselect v-model="target.rot_mode" label="Slit Position" field="rot_mode" v-on:input="update" :errors="errors.rot_mode"
                           :options="[{value: 'VFLOAT', text: 'Parallactic'}, {value: 'SKY', text: 'User Specified'}]"
                           desc="With the slit at the parallactic angle, atmospheric dispersion is along the slit.">
            </customselect>
            <customfield v-model="target.rot_angle" label="Angle" field="rot_angle" v-on:input="update"
                         :errors="errors.rot_angle" v-if="target.rot_mode === 'SKY'"
                         desc="Position Angle of the slit in degrees east of north.">
            </customfield>
          </div>
        </form>
      </div>
    </div>
  </panel>
</template>
<script>
import _ from 'lodash';
import $ from 'jquery';

import {collapseMixin, sexagesimalRaToDecimal, sexagesimalDecToDecimal} from '../utils.js';
import archive from './archive.vue';
import panel from './util/panel.vue';
import customfield from './util/customfield.vue';
import customselect from './util/customselect.vue';
export default {
  props: ['target', 'errors', 'datatype', 'selectedinstrument', 'parentshow', 'simple_interface'],
  components: {customfield, customselect, panel, archive},
  mixins: [collapseMixin],
  data: function(){
    var ns_target_params = {
      scheme: 'MPC_MINOR_PLANET',
      orbinc: null,
      longascnode: null,
      argofperih: null,
      eccentricity: null,
      meandist: null,
      meananom: null,
      perihdist: null,
      epochofperih: null
    };
    var rot_target_params = {rot_mode: 'VFLOAT', rot_angle: 0};
    var sid_target_params = _.cloneDeep(this.target);
    delete sid_target_params['name'];
    delete sid_target_params['type'];
    return {
      show: true,
      showSlitPosition: false,
      lookingUP: false,
      lookupFail: false,
      lookupText: '',
      lookupReq: undefined,
      ns_target_params: ns_target_params,
      sid_target_params: sid_target_params,
      rot_target_params: rot_target_params
    };
  },
  methods: {
    update: function(){
      this.$emit('targetupdate', {});
    },
    updateRA: function(){
      this.target.ra = sexagesimalRaToDecimal(this.target.ra);
      this.update();
    },
    updateDec: function(){
      this.target.dec = sexagesimalDecToDecimal(this.target.dec);
      this.update();
    }
  },
  watch: {
    'target.name': _.debounce(function(name){
      if(this.target.type === 'SIDEREAL'){
        this.lookingUP = true;
        this.lookupFail = false;
        this.lookupText = 'Searching for coordinates...';
        var that = this;
        if(this.lookupReq){
          this.lookupReq.abort();
        }
        this.lookupReq = $.getJSON('https://lco.global/lookUP/json/?name=' + name).done(function(data){
          that.target.ra = _.get(data, ['ra', 'decimal'], null);
          that.target.dec = _.get(data, ['dec', 'decimal'], null);
          that.target.proper_motion_ra = data.pmra;
          that.target.proper_motion_dec = data.pmdec;
          that.update();
        }).fail(function(_response, status){
          if(status !== "abort"){
            that.lookupText = 'Could not find any matching objects';
            that.lookupFail = true;
          }
        }).always(function(_response, status){
          if(status !== "abort"){
            that.lookingUP = false;
          }
        });
      }
    }, 500),
    'datatype': function(value){
      if(value === 'SPECTRA'){
        for(var x in this.rot_target_params){
          this.target[x] = this.rot_target_params[x];
        }
      }else{
        for(var y in this.rot_target_params){
          this.rot_target_params[y] = this.target[y];
          this.target[y] = undefined;
        }
      }
    },
    selectedinstrument: function(value){
      if(value.includes('NRES')){
        this.showSlitPosition = false;
      }
      else if(this.datatype === 'SPECTRA'){
        this.showSlitPosition = true;
      }
    },
    'target.type': function(value){
      var that = this;
      if(value === 'SIDEREAL'){
        for(var x in that.ns_target_params){
          that.ns_target_params[x] = that.target[x];
          that.target[x] = undefined;
        }
        for(var y in that.sid_target_params){
          that.target[y] = that.sid_target_params[y];
        }
      }else if(value === 'NON_SIDEREAL'){
        for(var z in this.sid_target_params){
          that.sid_target_params[z] = that.target[z];
          that.target[z] = undefined;
        }
        for(var a in that.ns_target_params){
          that.target[a] = that.ns_target_params[a];
        }
      }
    }
  },
};
</script>
