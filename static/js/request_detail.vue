<template>
<div class="row request-details">
  <div class="col-md-12">
    <ul class="nav nav-tabs nav-justified">
      <li :class="{ active: tab === 'details' }" v-on:click="tab = 'details'">
        <a title="Details about the observed request.">Details</a>
      </li>
      <li :class="{ active: tab === 'scheduling' }" v-on:click="tab = 'scheduling'">
        <a title="Scheduling history.">Scheduling</a>
      </li>
      <li :class="{ active: tab === 'visibility' }" v-on:click="tab = 'visibility'">
        <a title="Target Visibility.">Visibility</a>
      </li>
      <li :class="{ active: tab === 'data' }" v-on:click="tab = 'data'">
        <a title="Downloadable data.">Data</a>
      </li>
    </ul>
    <div class="tab-content">
      <div class="tab-pane" :class="{ active: tab === 'details' }">
        <div class="row">
          <div class="col-md-6">
            <h4>Windows</h4>
            <table class="table">
              <thead>
                <tr><td><strong>Start</strong></td><td><strong>End</strong></td></tr>
              </thead>
              <tbody>
                <tr v-for="window in request.windows">
                  <td>{{ window.start | formatDate }}</td><td>{{ window.end | formatDate }}</td>
                </tr>
              </tbody>
            </table>
            <h4>Configurations</h4>
            <table class="table table-condensed">
              <thead>
                <tr>
                  <td><strong>Instrument Code</strong></td>
                  <td><strong>Filter</strong></td>
                  <td><strong>Exposures</strong></td>
                  <td><strong>Binning</strong></td>
                  <td><strong>Defocus</strong></td></td>
                </tr>
              </thead>
              <tbody>
                <tr v-for="molecule in request.molecules">
                  <td>{{ molecule.instrument_name }}</td>
                  <td>{{ molecule.filter }}</td>
                  <td>{{ molecule.exposure_time }} x {{ molecule.exposure_count }}</td>
                  <td>{{ molecule.bin_x }}</td>
                  <td>{{ molecule.defocus }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="col-md-6">
            <h4>Target</h4>
            <dl class="twocol dl-horizontal">
              <span v-for="x, idx in request.target">
              <dt v-if="request.target[idx]">{{ idx | formatField }}</dt>
              <dd v-if="x">{{ x | formatValue }}</dd>
              </span>
            </dl>
            <hr/>
            <h4>Constraints</h4>
            <dl class="twocol dl-horizontal">
              <span v-for="x, idx in request.constraints">
              <dt v-if="request.constraints[idx]">{{ idx | formatField }}</dt>
              <dd v-if="x">{{ x }}</dd>
              </span>
            </dl>
            <dl class="twocol dl-horizontal">
              <dt>Completion Threshold</dt>
              <dd>{{ request.completion_threshold }}%</dd>
            </dl>
          </div>
        </div>
      </div>
      <div class="tab-pane" :class="{ active: tab === 'data' }">
        <div class="row">
          <div v-if="request.state === 'COMPLETED'" class="col-md-4">
            <p v-show="curFrame" class="thumb-help">Click a row in the data table to preview the file below. Click preview for a larger version.</p>
            <thumbnail v-show="curFrame" :frame="curFrame" width="400" height="400"></thumbnail>
            <p v-show="curFrame && canViewColor">
                RVB frames found.
                <a v-on:click="viewColorImage" title="Color Image">
                  View color image <i class="fa fa-external-link"></i>
                </a><br/>
                <span v-show="loadingColor"><i class="fa fa-spin fa-spinner"></i> Generating color image...</span>
            </p>
          </div>
          <div :class="[(request.state === 'COMPLETED') ? 'col-md-8' : 'col-md-12']">
            <archivetable :requestid="request.id" v-on:rowClicked="curFrame = $event" v-on:dataLoaded="frames = $event"></archivetable>
          </div>
        </div>
      </div>
      <div class="tab-pane" :class="{ active: tab === 'scheduling' }">
        <blockhistory v-show="blockData.length > 0" :data="blockData" :showPlotControls="true"></blockhistory>
        <div v-show="blockData.length < 1" class="text-center"><h3>This request has not been scheduled.</h3></div>
      </div>
      <div class="tab-pane" :class="{ active: tab === 'visibility' }">
        <airmass_telescope_states v-show="'airmass_limit' in airmassData" :airmassData="airmassData"
                                  :telescopeStatesData="telescopeStatesData" :activeBlock="activeBlock"></airmass_telescope_states>
      </div>
    </div>
  </div>
</div>
</template>
<script>
import Vue from 'vue';
import $ from 'jquery';
import thumbnail from './components/thumbnail.vue';
import archivetable from './components/archivetable.vue';
import blockhistory from './components/blockhistory.vue';
import airmass_telescope_states from './components/airmass_telescope_states.vue';
import {formatDate, formatField} from './utils.js';
import {login, getLatestFrame} from './archive.js';

Vue.filter('formatDate', function(value){
  return formatDate(value);
});

Vue.filter('formatField', function(value){
  return formatField(value);
});

Vue.filter('formatValue', function(value){
  if(!isNaN(value)){
    return Number(value).toFixed(4);
  }
  return value;
});

export default {
  name: 'app',
  components: {thumbnail, archivetable, blockhistory, airmass_telescope_states},
  data: function(){
    return {
      request: {},
      frames: [],
      curFrame: null,
      blockData: [],
      activeBlock: null,
      airmassData: {},
      telescopeStatesData: {},
      tab: 'details',
      loadingColor: false
    };
  },
  created: function(){
    var requestId = $('#request-detail').data('requestid');
    var that = this;
    login(function(){
      $.getJSON('/api/requests/' + requestId, function(data){
        that.request = data;
        if(data.state === 'COMPLETED'){
          getLatestFrame(data.id, function(frame){
            that.curFrame = frame;
          });
        }
      });
    });
  },
  watch: {
    'tab': function(tab){
      if(tab === 'scheduling' && this.blockData.length === 0){
        this.loadBlockData();
      }
      else if (tab === 'visibility'){
        if($.isEmptyObject(this.airmassData)) {
          this.loadAirmassData();
        }
        if($.isEmptyObject(this.telescopeStatesData)){
          this.loadTelescopeStatesData();
          if(this.blockData.length === 0){
            this.loadBlockData();
          }
        }
      }
    }
  },
  computed: {
    colorImage: function(){
      if(this.curFrame){
        return 'https://thumbnails.lco.global/' + this.curFrame.id + '/?width=4000&height=4000&color=true';
      }else{
        return '';
      }
    },
    canViewColor: function(){
      var colorFilters = {
        'red': ['R', 'rp'],
        'visual': ['V'],
        'blue': ['B']
      };
      var filtersUsed = this.frames.map(function(frame){return frame.FILTER;});
      var numColors = 0;
      for(var color in colorFilters){
        for(var filter in colorFilters[color]){
          if(filtersUsed.includes(colorFilters[color][filter])){
            numColors += 1;
            break;
          }
        }
      }
      return numColors >= 3 ? true : false;
    }
  },
  methods: {
    loadBlockData: function(){
      var that = this;
      var requestId = $('#request-detail').data('requestid');
      $.getJSON('/api/requests/' + requestId + '/blocks/', function(data){
        that.blockData = data;
        for(var blockIdx in that.blockData){
          if(that.blockData[blockIdx].completed){
            that.activeBlock = that.blockData[blockIdx];
            break;
          }
          else if(that.blockData[blockIdx].status === 'SCHEDULED'){
            that.activeBlock = that.blockData[blockIdx];
          }
        }
      });
    },
    loadAirmassData: function(){
      var that = this;
      var requestId = $('#request-detail').data('requestid');
      $.getJSON('/api/requests/' + requestId + '/airmass/', function(data){
        that.airmassData = data;
      });
    },
    loadTelescopeStatesData: function(){
      var that = this;
      var requestId = $('#request-detail').data('requestid');
      $.getJSON('/api/requests/' + requestId + '/telescope_states/', function(data){
        that.telescopeStatesData = data;
      });
    },
    viewColorImage: function(){
      var that = this;
      this.loadingColor = true;
      $.getJSON(this.colorImage, function(data){
        that.loadingColor = false;
        window.open(data['url'], '_blank');
      });
    }
  }

};
</script>
<style>
dl.twocol {
  -moz-column-count: 2;
  -webkit-column-count: 2;
  column-count: 2;
}

dl.twocol dt {
  width: inherit;
}

.request-details {
  margin-top: 5px;
}
.thumb-help {
  font-style: italic;
  font-size: 0.8em;
}
.tab-pane {
  padding-top: 5px;
}
</style>
