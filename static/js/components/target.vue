<template>
  <panel :id="'target' + $parent.index" :errors="errors" v-on:show="show = $event"
         :canremove="false" :cancopy="false" icon="fa-crosshairs" title="Target" :show="show">
    <div v-for="error in errors.non_field_errors" class="alert alert-danger" role="alert">{{ error }}</div>
    <div class="row">
      <div class="col-md-6 compose-help" v-show="show">
      </div>
      <div :class="show ? 'col-md-6' : 'col-md-12'">
        <form class="form-horizontal">
          <customfield v-model="target.name" label="Target Name" field="name" v-on:input="update" :errors="errors.name">
          </customfield>
          <div class="row" v-show="lookingUP">
              <span class="col-md-12" style="text-align: right">
                <i class="fa fa-spinner fa-spin fa-fw"></i> Looking up coordinates...
              </span>
          </div>
          <customselect v-model="target.type" label="Type" field="type" v-on:input="update"
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
                         v-on:input="update" :errors="errors.proper_motion_ra" desc="&plusmn;0.33 mas/year">
            </customfield>
            <customfield v-model="target.proper_motion_dec" label="Proper Motion: Dec" field="proper_motion_dec"
                         v-on:input="update" :errors="errors.proper_motion_dec" desc="&plusmn;0.33 mas/year">
            </customfield>
            <customfield v-model="target.epoch" label="Epoch" field="epoch" v-on:input="update" :errors="errors.epoch" desc="Julian Years">
            </customfield>
            <customfield v-model="target.parallax" label="Parallax" field="parallax" v-on:input="update"
                         :errors="errors.parallax" desc="+0.45 mas">
            </customfield>
          </div>
          <div class="non-sidereal" v-show="target.type === 'NON_SIDEREAL'">
            <customselect v-model="target.scheme" label="Scheme" field="scheme" v-on:input="update" :errors="errors.scheme"
                          :options="[{value: 'MPC_MINOR_PLANET', text: 'MPC Minor Planet'}, {value: 'MPC_COMET', text: 'MPC Comet'}]"
                          desc="The orbital elements scheme to use with this target.">
            </customselect>
            <customfield v-model="target.epoch" label="Epoch" field="epoch" v-on:input="update" :errors="errors.epoch"
                         desc="Modified Julian Days">
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
            <customfield v-model="target.meandist" label="Mean Distance (AU)" field="meandist"
                          v-on:input="update" :errors="errors.meandist" desc="Astronomical Units">
            </customfield>
            <customfield v-model="target.eccentricity" label="Eccentricity" field="eccentricity"
                          v-on:input="update" :errors="errors.eccentricity" desc="0 to 0.99">
            </customfield>
            <customfield v-model="target.meananom" label="Mean Anomoly" field="meananom"
                          v-on:input="update" :errors="errors.meananom" desc="Angle in Degrees">
            </customfield>
          </div>
          <div class="spectra" v-if="datatype === 'SPECTRA'">
            <customselect v-model="target.rot_mode" label="Rotator Mode" field="rot_mode" v-on:input="update" :errors="errors.rot_mode"
                           :options="[{value: 'SKY', text: 'Sky'}, {value: 'VFLOAT', text: 'Vertical Floating'}]">
            </customselect>
            <customfield v-model="target.rot_angle" label="Rotator Angle" field="rot_angle" v-on:input="update" :errors="errors.rot_angle">
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
import panel from './util/panel.vue';
import customfield from './util/customfield.vue';
import customselect from './util/customselect.vue';
export default {
  props: ['target', 'errors', 'datatype', 'parentshow'],
  components: {customfield, customselect, panel},
  mixins: [collapseMixin],
  data: function(){
    var ns_target_params = {
      scheme: 'MPC_MINOR_PLANET',
      orbinc: 0,
      longascnode: 0,
      argofperih: 0,
      meandist: 0,
      eccentricity: 0,
      meananom: 0
    };
    var rot_target_params = {rot_mode: 'SKY', rot_angle: 0};
    var sid_target_params = _.cloneDeep(this.target);
    delete sid_target_params['name'];
    delete sid_target_params['epoch'];
    delete sid_target_params['type'];
    return {show: true, lookingUP: false, ns_target_params: ns_target_params, sid_target_params: sid_target_params, rot_target_params: rot_target_params};
  },
  methods: {
    update: function(){
      this.$emit('targetupdate', {});
    },
    updateRA: function(){
      this.ra = sexagesimalRaToDecimal(this.ra);
      this.update();
    },
    updateDec: function(){
      this.dec = sexagesimalDecToDecimal(this.dec);
      this.update();
    }
  },
  watch: {
    'target.name': _.debounce(function(name){
      this.lookingUP = true;
      var that = this;
      $.getJSON('https://lco.global/lookUP/json/?name=' + name).done(function(data){
        that.target.ra = _.get(data, ['ra', 'decimal'], null);
        that.target.dec = _.get(data, ['dec', 'decimal'], null);
        that.target.proper_motion_ra = data.pmra;
        that.target.proper_motion_dec = data.pmdec;
        that.update();
      }).always(function(){
        that.lookingUP = false;
      });
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
    'target.type': function(value){
      var that = this;
      if(this.target.type === 'SIDEREAL'){
        for(var x in this.ns_target_params){
          that.ns_target_params[x] = that.target[x];
          that.target[x] = undefined;
        }
        for(var y in this.sid_target_params){
          that.target[y] = that.sid_target_params[y];
        }
      }else if(value === 'NON_SIDEREAL'){
        for(var z in this.sid_target_params){
          that.sid_target_params[z] = that.target[z];
          that.target[z] = undefined;
        }
        for(var a in this.ns_target_params){
          that.target[a] = that.ns_target_params[a];
        }
      }
    }
  },
};
</script>